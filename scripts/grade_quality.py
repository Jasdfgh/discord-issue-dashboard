#!/usr/bin/env python3
"""
Quality grading CLI — run manually or via cron.

Usage:
    python scripts/grade_quality.py           # Grade ungraded/changed issues
    python scripts/grade_quality.py --status  # Show grading progress
    python scripts/grade_quality.py --regrade # Force re-grade all issues
"""

import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.db import init_database, get_grading_stats
from utils.logger import setup_logger

logger = setup_logger("grade")


def main():
    parser = argparse.ArgumentParser(description="Quality grading with Claude")
    parser.add_argument("--status", action="store_true", help="Show grading progress")
    parser.add_argument("--regrade", action="store_true", help="Force re-grade all")
    args = parser.parse_args()

    init_database()

    if args.status:
        stats = get_grading_stats()
        logger.info(f"Total: {stats['total']} | Graded: {stats['graded']} | Ungraded: {stats['ungraded']}")
        return

    if args.regrade:
        from utils.db import get_connection
        logger.info("Clearing all grades for re-grading...")
        with get_connection() as conn:
            conn.execute("DELETE FROM quality_grades")
            conn.commit()

    from utils.grading import run_grading

    def on_progress(done, total):
        logger.info(f"  Progress: {done}/{total}")

    logger.info("=" * 50)
    logger.info("Starting quality grading")
    logger.info("=" * 50)

    result = run_grading(on_progress=on_progress)

    logger.info("=" * 50)
    logger.info(f"Done: {result['graded']} graded, {result['skipped']} skipped, {result['failed']} failed")
    logger.info("=" * 50)

    stats = get_grading_stats()
    logger.info(f"Overall: {stats['graded']}/{stats['total']} graded")


if __name__ == "__main__":
    main()
