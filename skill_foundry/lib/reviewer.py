"""Promotion reviewer — an LLM judge (or interactive fallback) for every promotion.

Review is ON by default for `promote` / `promote-skill`: the gates run, then the
judge must APPROVE before anything is applied. Set SKILL_REVIEWER to a shell
command that reads the diff on **stdin** and prints a single verdict word —
APPROVE, HOLD, or REJECT. If unset, review falls back to an interactive prompt
(you — slower, but no LLM dependency); pass `--no-review` to skip the judge.

Example (Claude Code CLI):
  export SKILL_REVIEWER='claude -p "You are a strict skill reviewer. Review the
  following diff for a promotion into the shared skills corpus. Reply exactly
  one word: APPROVE, HOLD, or REJECT."'
"""

from __future__ import annotations

import os
import re
import subprocess
import sys


def llm_verdict(diff_text: str) -> str | None:
    """Return 'approve' | 'hold' | 'reject', or None if no reviewer configured."""
    cmd = os.environ.get("SKILL_REVIEWER")
    if not cmd:
        return None
    try:
        r = subprocess.run(cmd, shell=True, input=diff_text,
                           capture_output=True, text=True, timeout=180)
    except Exception as exc:  # pragma: no cover - environmental
        print(f"reviewer error: {exc}", file=sys.stderr)
        return None
    out = ((r.stdout or "") + " " + (r.stderr or "")).upper()
    m = re.search(r"\b(APPROVE|HOLD|REJECT)\b", out)
    return m.group(1).lower() if m else None


def can_review() -> bool:
    """True if a review can actually happen: an LLM reviewer is configured, or stdin is interactive."""
    return bool(os.environ.get("SKILL_REVIEWER")) or sys.stdin.isatty()


def approve(diff_text: str) -> bool:
    """Return True if the promotion is approved (LLM judge, else interactive)."""
    v = llm_verdict(diff_text)
    if v is not None:
        print(f"review verdict: {v.upper()}")
        return v == "approve"
    # interactive fallback (no SKILL_REVIEWER configured)
    print(diff_text)
    print()
    try:
        ans = input("Promote? [a]pprove / [h]old / [r]eject: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("(no input — holding)", file=sys.stderr)
        return False
    return ans in ("a", "approve", "y", "yes")


if __name__ == "__main__":
    # test helper: echo the verdict for a pasted diff
    print(llm_verdict(sys.stdin.read()) or "no reviewer configured")
