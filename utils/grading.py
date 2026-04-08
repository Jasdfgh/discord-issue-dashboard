"""
Quality Grading Engine — Claude-based blind quality assessment.

Uses utils/llm.call_llm() which routes to Cursor CLI or API.
Owner field is intentionally excluded from the prompt for fairness.
"""

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import LLM_GRADE_BATCH_SIZE

logger = logging.getLogger("discord_dashboard.grading")

GRADING_SYSTEM_PROMPT = """\
You are an AMD developer community technical support quality reviewer.

For each support ticket, classify the RESPONSE quality:
- High: Response addresses AI/AMD-GPU technical issues with concrete help \
(specific solutions, code, version numbers, actionable steps, or deep diagnosis)
- Medium: Response addresses AI/AMD-GPU topics but only provides general direction \
or basic information relay
- Low: Not AI/GPU technical content (hardware repair, gaming, news relay, social chat, \
internal process records, spam reports, etc.), or response provides no substantive help"""


def _build_batch_prompt(batch: List[Dict[str, Any]]) -> str:
    """Build prompt for a batch of tickets. Owner is excluded for blind grading."""
    lines = ["Classify each ticket below. Output exactly one line per ticket: [ID]: High/Medium/Low\n"]
    for item in batch:
        lines.append(f"---\n[{item['id']}]")
        lines.append(f"Channel: {item.get('channel', '') or 'N/A'}")
        lines.append(f"Problem Type: {item.get('problem_category', '') or 'N/A'}")
        lines.append(f"Issue Topic: {item.get('category', '') or 'N/A'}")
        lines.append(f"Issue: {item.get('issue', '') or 'N/A'}")
        lines.append(f"Reply: {item.get('reply_approach', '') or 'N/A'}")
    return "\n".join(lines)


def _parse_batch_response(text: str) -> Dict[int, str]:
    """Parse Claude's response into {issue_id: grade}."""
    results = {}
    for line in text.strip().splitlines():
        m = re.match(r"\[?(\d+)\]?\s*:\s*(High|Medium|Low)", line, re.IGNORECASE)
        if m:
            issue_id = int(m.group(1))
            grade = m.group(2).capitalize()
            if grade in ("High", "Medium", "Low"):
                results[issue_id] = grade
    return results


def compute_content_hash(item: Dict[str, Any]) -> str:
    """Hash of the fields that determine quality grade. If content changes, re-grade."""
    parts = [
        str(item.get("reply_approach", "")),
        str(item.get("problem_category", "")),
        str(item.get("category", "")),
        str(item.get("issue", "")),
        str(item.get("channel", "")),
    ]
    return hashlib.md5("|".join(parts).encode()).hexdigest()


def grade_batch(batch: List[Dict[str, Any]]) -> Dict[int, str]:
    """Send a batch to Claude and return {issue_id: grade}."""
    from utils.llm import call_llm

    prompt = _build_batch_prompt(batch)
    response_text = call_llm(prompt, system_prompt=GRADING_SYSTEM_PROMPT, timeout=180)
    return _parse_batch_response(response_text)


def run_grading(on_progress: Optional[callable] = None) -> Dict[str, int]:
    """
    Main grading loop with parallel workers.

    Splits ungraded/changed issues into batches, runs them concurrently
    via ThreadPoolExecutor, then persists all results.

    on_progress(processed_so_far, total_to_grade) is called after each batch.
    Returns {"graded": N, "skipped": N, "failed": N}.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading
    from utils.db import get_issues_needing_grading, upsert_quality_grades
    from config import LLM_CLI_MODEL, LLM_GRADE_WORKERS

    all_issues = get_issues_needing_grading()

    to_grade = []
    for item in all_issues:
        current_hash = compute_content_hash(item)
        if item["old_hash"] is None or item["old_hash"] != current_hash:
            item["_new_hash"] = current_hash
            to_grade.append(item)

    if not to_grade:
        logger.info("All issues already graded and up-to-date.")
        return {"graded": 0, "skipped": len(all_issues), "failed": 0}

    batches = [
        to_grade[i : i + LLM_GRADE_BATCH_SIZE]
        for i in range(0, len(to_grade), LLM_GRADE_BATCH_SIZE)
    ]
    workers = min(LLM_GRADE_WORKERS, len(batches))
    logger.info(
        f"Grading {len(to_grade)} issues: {len(batches)} batches × {LLM_GRADE_BATCH_SIZE}, "
        f"{workers} parallel workers"
    )

    now = datetime.now(timezone.utc).isoformat()
    results_to_save = []
    graded_count = 0
    failed_count = 0
    lock = threading.Lock()
    processed = [0]

    def _process_batch(batch):
        batch_ids = [item["id"] for item in batch]
        try:
            grades = grade_batch(batch)
            return batch, grades, None
        except Exception as e:
            logger.error(f"Batch {batch_ids} failed: {e}")
            return batch, {}, e

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_process_batch, b): b for b in batches}

        for future in as_completed(futures):
            batch, grades, error = future.result()

            with lock:
                if error:
                    failed_count += len(batch)
                else:
                    for item in batch:
                        grade = grades.get(item["id"])
                        if grade:
                            results_to_save.append({
                                "issue_id": item["id"],
                                "quality_grade": grade,
                                "content_hash": item["_new_hash"],
                                "graded_at": now,
                                "model_used": LLM_CLI_MODEL,
                            })
                            graded_count += 1
                        else:
                            failed_count += 1

                processed[0] += len(batch)
                if on_progress:
                    on_progress(processed[0], len(to_grade))

    upsert_quality_grades(results_to_save)
    logger.info(f"Grading complete: {graded_count} graded, {failed_count} failed")
    return {
        "graded": graded_count,
        "skipped": len(all_issues) - len(to_grade),
        "failed": failed_count,
    }
