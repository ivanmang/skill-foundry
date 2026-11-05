#!/usr/bin/env python3
"""Draft learnings from a pi session transcript (session-end capture).

Turns the *interactive* triage findings — the ones a run record can't see —
into strict-format LRN drafts. Extracts the user/assistant turns from a pi
session .jsonl, asks a configured LLM to list reusable learnings, and appends
them as `pending` to learnings/recent.md (or prints them).

Usage:
  ./harness capture-session                              # $PI_SESSION_FILE
  ./harness capture-session --session ~/.pi/agent/sessions/.../X.jsonl --apply
  SKILL_CAPTURER="pi -p ..." ./harness capture-session
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

from skill_foundry.paths import ROOT as HARNESS  # noqa: E402
from skill_foundry.lib import log_correction  # noqa: E402

DEFAULT_FILE = HARNESS / "learnings" / "recent.md"

CAPTURER_PROMPT = (
    "You are a learning-capture assistant for a skill library. The session transcript is on stdin "
    "(user and assistant turns). List only REUSABLE learnings: bugs fixed, non-obvious conventions, "
    "tool/config behaviors worth remembering, or corrections. "
    "Ignore chit-chat and one-off details.\n"
    "Output exactly one line per learning, nothing else (no prose, no code fences, no markdown):\n"
    "LRN|category|context|skill|wrong|correct|action\n"
    "category ∈ {correction,error,knowledge_gap,feature}. context = short trigger or run-id. "
    "skill = target skill (default pto-isa). wrong = symptom / what happened. "
    "correct = what should happen instead. action = where to update (mention known-failures if triage). "
    "Do not use the pipe character inside any field."
)

DEFAULT_CAPTURER = (
    "pi -p --no-tools --no-extensions --no-skills --no-context-files --no-mcp --thinking low"
)


def _message_text(msg: dict) -> str:
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text" and block.get("text"):
                    parts.append(block["text"])
                elif isinstance(block.get("text"), str):
                    parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return ""


def extract_transcript(session_path: Path, max_chars: int) -> str:
    turns: list[str] = []
    with session_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("type") != "message":
                continue
            message = rec.get("message") or {}
            role = message.get("role")
            if role not in ("user", "assistant"):
                continue
            text = _message_text(message).strip()
            if text:
                turns.append(f"### {role}\n{text}")

    transcript = "\n\n".join(turns)
    if len(transcript) > max_chars:
        transcript = transcript[-max_chars:]
        transcript = f"(transcript truncated to last {max_chars} chars)\n\n" + transcript
    return transcript


def run_capturer(transcript: str, capturer: str) -> str:
    argv = shlex.split(capturer)
    if not argv:
        raise ValueError("empty capturer command")
    # The instruction is appended as the prompt; the transcript rides on stdin.
    argv.append(CAPTURER_PROMPT)
    result = subprocess.run(
        argv, input=transcript + "\n\n---END OF TRANSCRIPT---", capture_output=True, text=True,
        timeout=300, check=False,
    )
    return (result.stdout or "") + "\n" + (result.stderr or "")


def parse_learnings(text: str, skill: str, context: str) -> list[dict]:
    out: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("LRN|"):
            continue
        parts = line.split("|")
        if len(parts) < 7:
            continue
        _, category, ctx, sk, wrong, correct, action = parts[:7]
        out.append({
            "category": (category or "correction").lower(),
            "context": ctx.strip() or context,
            "skill": sk.strip() or skill,
            "wrong": wrong.strip(),
            "correct": correct.strip(),
            "action": action.strip(),
        })
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Draft learnings from a pi session transcript.")
    ap.add_argument("--session", default=os.environ.get("PI_SESSION_FILE"),
                    help="Session .jsonl (default $PI_SESSION_FILE).")
    ap.add_argument("--skill", default="pto-isa")
    ap.add_argument("--context", default=None)
    ap.add_argument("--apply", action="store_true", help="Append pending drafts (default: print).")
    ap.add_argument("--file", default=str(DEFAULT_FILE))
    ap.add_argument("--max-chars", type=int, default=40000)
    ap.add_argument("--capturer", default=os.environ.get("SKILL_CAPTURER", DEFAULT_CAPTURER),
                    help="LLM command to judge the transcript (reads stdin).")
    args = ap.parse_args(argv)

    if not args.session:
        print("No session file (-s) and $PI_SESSION_FILE is unset.", file=sys.stderr)
        return 2
    session_path = Path(args.session).expanduser()
    if not session_path.exists():
        print(f"session file not found: {session_path}", file=sys.stderr)
        return 2

    transcript = extract_transcript(session_path, args.max_chars)
    if not transcript.strip():
        print("no user/assistant turns found in the session file.", file=sys.stderr)
        return 1

    try:
        raw = run_capturer(transcript, args.capturer)
    except Exception as exc:
        print(f"capturer failed: {exc}", file=sys.stderr)
        return 1

    entries = parse_learnings(raw, args.skill, args.context or "session-capture")
    if not entries:
        print("capturer returned no LRN|... lines (nothing to capture).")
        return 0

    if args.apply:
        for entry in entries:
            log_correction.append_entry(args.file, entry)
        print(f"capture-session: appended {len(entries)} pending draft(s) → {args.file}")
    else:
        for i, entry in enumerate(entries):
            print(log_correction.format_entry({**entry, "id": f"LRN-DRAFT-{i + 1:03d}", "status": "pending"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())