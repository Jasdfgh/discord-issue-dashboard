"""
Unified LLM interface — Cursor CLI (primary) + Anthropic API (backup).

call_llm() is the single entry point used by grading.py and report.py.
Backend selection: config.LLM_BACKEND ("cli" or "api").
"""

import logging
import shutil
import subprocess
from typing import Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    LLM_BACKEND, LLM_CLI_MODEL, LLM_CLI_BINARY,
    LLM_API_BASE_URL, LLM_API_KEY, LLM_API_MODEL,
)

logger = logging.getLogger("discord_dashboard.llm")


def call_llm(prompt: str, system_prompt: Optional[str] = None, timeout: int = 120) -> str:
    """
    Send a prompt to the LLM and return the text response.

    Tries CLI first (if configured), falls back to API.
    system_prompt is prepended to the user prompt for CLI mode.
    """
    if LLM_BACKEND == "cli":
        return _call_cli(prompt, system_prompt, timeout)
    elif LLM_BACKEND == "api":
        return _call_api(prompt, system_prompt, timeout)
    else:
        raise RuntimeError(f"Unknown LLM_BACKEND: {LLM_BACKEND}")


def _call_cli(prompt: str, system_prompt: Optional[str], timeout: int) -> str:
    """Call Cursor Agent CLI in headless mode."""
    binary = shutil.which(LLM_CLI_BINARY)
    if not binary:
        raise RuntimeError(
            f"Cursor CLI '{LLM_CLI_BINARY}' not found in PATH. "
            "Install: curl https://cursor.com/install -fsSL | bash"
        )

    full_prompt = prompt
    if system_prompt:
        full_prompt = f"{system_prompt}\n\n---\n\n{full_prompt}"

    cmd = [
        binary,
        "--print",
        "--model", LLM_CLI_MODEL,
        "--trust",
        "--mode", "ask",
        "--output-format", "text",
        full_prompt,
    ]

    logger.debug(f"CLI call: model={LLM_CLI_MODEL}, prompt_len={len(full_prompt)}")

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout,
    )

    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Cursor CLI failed (exit {result.returncode}): {err[:300]}")

    response = result.stdout.strip()
    if not response:
        raise RuntimeError("Cursor CLI returned empty response")

    logger.debug(f"CLI response: {len(response)} chars")
    return response


def _call_api(prompt: str, system_prompt: Optional[str], timeout: int) -> str:
    """Call internal API gateway (Anthropic SDK). Backup path."""
    if not LLM_API_BASE_URL:
        raise RuntimeError("LLM_API_BASE_URL not configured for API backend.")

    from anthropic import Anthropic

    client = Anthropic(
        base_url=LLM_API_BASE_URL,
        api_key="dummy",
        default_headers={"Ocp-Apim-Subscription-Key": LLM_API_KEY},
    )

    kwargs = {
        "model": LLM_API_MODEL,
        "max_tokens": 16000,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": "max"},
        "messages": [{"role": "user", "content": prompt}],
    }
    if system_prompt:
        kwargs["system"] = system_prompt

    message = client.messages.create(**kwargs)

    for block in message.content:
        if block.type == "text":
            return block.text
    return ""


def is_llm_available() -> bool:
    """Check if any LLM backend is usable (for UI status display)."""
    if LLM_BACKEND == "cli":
        return shutil.which(LLM_CLI_BINARY) is not None
    elif LLM_BACKEND == "api":
        return bool(LLM_API_BASE_URL)
    return False
