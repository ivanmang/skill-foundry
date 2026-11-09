"""Promotion reviewer — a real judge, not a rubber stamp.

Review runs on every promotion (`promote` / `promote-skill`) after the mechanical
gates and before anything is written. It is two layers:

1. **Built-in deterministic review** (always runs, no config) — catches the
   *structural* bad-judgment cases a diff can't hide:
   - dangling cross-skill references (skill: / ../X/SKILL.md / skills/X/)
   - secrets slipped into the added content
   - placeholder markers (TODO / FIXME / TBD / …)
   - contradictions and near-duplicates against the target's existing checks

2. **LLM judge** (`SKILL_REVIEWER`, **required**) — the *semantic* layer. A
   shell command that reads the diff on stdin and prints APPROVE / HOLD / REJECT.
   Without it there is no semantic review: in an interactive session the human
   is asked; otherwise the promotion fails closed.

The final verdict is the most restrictive of the two (and the human merge at the
end is always the final gate).

Example:
  export SKILL_REVIEWER='claude -p "Strict skill reviewer. Review the diff on
  stdin. Reply exactly one word: APPROVE, HOLD, or REJECT."'
"""

from __future__ import annotations

import difflib
import os
import re
import shlex
import subprocess
import sys

from skill_foundry.paths import ROOT  # noqa: E402
from skill_foundry.lib import gates, metrics, validate_skills  # noqa: E402

_VERDICT_ORDER = {"reject": 0, "hold": 1, "approve": 2}

_NEGATION_MARKERS = (
    "never",
    "do not",
    "don't",
    "forbid",
    "forbidden",
    "must not",
    "should not",
    "禁止",
    "不得",
    "严禁",
)

_PLACEHOLDER_MARKERS = ("todo", "fixme", "tbd", "xxx", "placeholder", "lorem ipsum")

_MIN_LINE = 20  # ignore very short added lines for conflict/duplicate checks


def _norm(s: str) -> str:
    s = (s or "").strip()
    # strip leading list markers / quotes
    s = re.sub(r"^[-*•#>]+", "", s).strip()
    return re.sub(r"\s+", " ", s).lower()


def _core(s: str) -> str:
    """Strip the '(was: …) — <context>' provenance suffix before comparing."""
    return _norm(re.sub(r"\s*\(was:.*$", "", s))


def _worst(a: str, b: str) -> str:
    return a if _VERDICT_ORDER[a] < _VERDICT_ORDER[b] else b


def _has_negation(s: str) -> bool:
    return any(k in s for k in _NEGATION_MARKERS)


def llm_verdict(diff_text: str) -> str | None:
    """Return 'approve' | 'hold' | 'reject', or None if no reviewer configured."""
    cmd = os.environ.get("SKILL_REVIEWER")
    if not cmd:
        return None
    # Run as an argv list (no shell) so a reviewer command can't inject shell.
    try:
        argv = shlex.split(cmd)
    except ValueError:
        argv = [cmd]
    if not argv:
        return None
    try:
        r = subprocess.run(
            argv, input=diff_text, capture_output=True, text=True, timeout=180
        )
    except Exception as exc:  # pragma: no cover - environmental
        print(f"reviewer error: {exc}", file=sys.stderr)
        return None
    out = ((r.stdout or "") + " " + (r.stderr or "")).upper()
    m = re.search(r"\b(APPROVE|HOLD|REJECT)\b", out)
    return m.group(1).lower() if m else None


def can_review() -> bool:
    """True if a review can happen: an LLM reviewer is configured or stdin is a TTY."""
    return bool(os.environ.get("SKILL_REVIEWER")) or sys.stdin.isatty()


def builtin_review(
    diff_text: str,
    target_content: str = "",
    added_text: str | None = None,
    local_skills: set[str] | None = None,
    externals: set[str] | None = None,
) -> tuple[str, list[str]]:
    """Deterministic review. Returns (verdict, reasons); verdict in approve|hold|reject."""
    if added_text is None:
        added_text = "\n".join(
            ln[1:]
            for ln in diff_text.splitlines()
            if ln.startswith("+") and not ln.startswith("+++")
        )
    if local_skills is None:
        sd = ROOT / ".claude" / "skills"
        local_skills = {
            d.name for d in sd.iterdir() if d.is_dir() and not d.name.startswith(".")
        }
    if externals is None:
        externals = validate_skills.load_external_names()

    reject: list[str] = []
    hold: list[str] = []

    # 1. dangling cross-skill references introduced by this change
    for pat in validate_skills.REF_PATTERNS:
        for m in pat.finditer(added_text):
            name = m.group(1)
            if name not in local_skills and name not in externals:
                reject.append(f"dangling reference to unknown skill '{name}'")

    # 2. secrets
    for pat in gates.SECRET_PATTERNS:
        if pat.search(added_text):
            reject.append("possible secret in added content")

    # 3. placeholder markers
    for kw in _PLACEHOLDER_MARKERS:
        if re.search(rf"\b{re.escape(kw)}\b", added_text, re.I):
            hold.append(f"placeholder marker '{kw}'")

    # 4. contradiction / near-duplicate vs the target's existing checks
    existing = [
        ln
        for ln in target_content.splitlines()
        if ln.strip() and not ln.lstrip().startswith(("#", "<!--"))
    ]
    added_lines = [ln for ln in added_text.splitlines() if ln.strip()]
    for aln in added_lines:
        a = _core(aln)
        if len(a) < _MIN_LINE:
            continue
        for eln in existing:
            e = _core(eln)
            if len(e) < _MIN_LINE:
                continue
            ratio = difflib.SequenceMatcher(None, a, e).ratio()
            if ratio >= 0.92:
                if _has_negation(a) != _has_negation(e):
                    reject.append(f"contradicts existing check: {eln.strip()[:70]}")
                else:
                    hold.append(f"near-duplicate of existing line: {eln.strip()[:70]}")
                break

    if reject:
        return "reject", reject
    if hold:
        return "hold", hold
    return "approve", []


def _record_judge(verdict: str, context: dict | None = None) -> None:
    eid = metrics.record("judge", verdict=verdict, **(context or {}))
    if eid:
        print(
            f"  · judge event {eid} — calibrate: ./harness metrics --calibrate {eid} approve|reject",
            file=sys.stderr,
        )


def approve(
    diff_text: str,
    target_content: str = "",
    added_text: str | None = None,
    context: dict | None = None,
) -> bool:
    """Return True if the promotion is approved (builtin judge + optional LLM)."""
    verdict, reasons = builtin_review(diff_text, target_content, added_text)
    if reasons:
        print("builtin review:", file=sys.stderr)
        for r in reasons:
            print(f"  ⚠ {r}", file=sys.stderr)
    if verdict == "reject":
        _record_judge("reject", context)
        print("review verdict: REJECT (builtin)")
        return False

    llm = llm_verdict(diff_text)
    if llm is not None:
        final = _worst(verdict, llm)
        _record_judge(final, context)
        print(f"review verdict: {final.upper()}")
        return final == "approve"

    # LLM judge is mandatory — no SKILL_REVIEWER configured.
    if not sys.stdin.isatty():
        print(
            "✗ SKILL_REVIEWER is required: set it to an LLM judge command "
            "(reads the diff on stdin, prints APPROVE/HOLD/REJECT), or run "
            "interactively.",
            file=sys.stderr,
        )
        return False

    # interactive fallback — a human is the judge
    print(diff_text)
    print()
    try:
        ans = (
            input("No SKILL_REVIEWER set — [a]pprove / [h]old / [r]eject: ")
            .strip()
            .lower()
        )
    except (EOFError, KeyboardInterrupt):
        print("(no input — holding)", file=sys.stderr)
        return False
    _record_judge(
        "approve" if ans in ("a", "approve", "y", "yes") else "reject", context
    )
    return ans in ("a", "approve", "y", "yes")


if __name__ == "__main__":
    v, rs = builtin_review(sys.stdin.read())
    print(f"verdict: {v}")
    for r in rs:
        print(f"  ⚠ {r}")
