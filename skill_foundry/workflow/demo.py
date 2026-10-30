#!/usr/bin/env python3
"""Interactive, step-by-step sandboxed demo tour of the skill-foundry.

No hardware / CANN / compiler needed: it drives the *real* harness scripts
against a mock gtest runner. Unlike demo/run_demo.sh (straight-through), this
is interactive — after every step you choose what to do next (run / next /
previous / jump / explain / quit) with arrow keys.

Usage:
  python3 -m skill_foundry.workflow.demo                 # interactive, step-by-step
  python3 -m skill_foundry.workflow.demo --straight      # run demo/run_demo.sh straight through
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

from skill_foundry.paths import ROOT as HARNESS  # noqa: E402
from skill_foundry.lib import ui  # noqa: E402 — reuse select_menu / banner / c / ask

DEMO_CONFIG = HARNESS / "demo" / "config" / "demo-suites.json"
DEMO_ARCHES = HARNESS / "demo" / "config" / "demo-arches.json"
BASELINE = HARNESS / "demo" / "baseline" / "demo-baseline.json"
KNOWN_BEFORE = HARNESS / "demo" / "fixtures" / "known-failures.before.md"
FAIL_CASE = "VecOpTest.case_vcvt_bf16fp16_128x128"

SANDBOX = Path(tempfile.mkdtemp(prefix="harness-demo."))
TARGET_REPO = SANDBOX / "target"
SB2 = SANDBOX / "harness"
RUN_ID = f"demo-live-{time.strftime('%Y%m%d-%H%M%S')}"
RUN_DIR = HARNESS / "reports" / RUN_ID
SB2_KNOWN = SB2 / ".claude" / "skills" / "pto-isa" / "references" / "known-failures.md"

SEP = "═" * 68


def _git(repo: Path, args: list[str]) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _run(cmd: list[str], check: bool = True) -> int:
    return subprocess.run([str(x) for x in cmd], cwd=HARNESS, check=check).returncode


def _grep(path: Path, needle: str) -> None:
    if not path.exists():
        print("    (no file yet)")
        return
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if needle in line:
            print(f"    {line.strip()}")
            return
    print("    (no matching line)")


def setup() -> None:
    """Create the sandbox: mock target repo + a disposable harness copy for the loop."""
    for d in glob.glob(str(HARNESS / "reports" / "demo-live-*")):
        shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(HARNESS / "demo" / "mockrepo", TARGET_REPO)
    _git(TARGET_REPO, ["init", "-q"])
    _git(TARGET_REPO, ["-c", "user.name=demo", "-c", "user.email=demo@example.com", "add", "-A"])
    _git(TARGET_REPO, ["-c", "user.name=demo", "-c", "user.email=demo@example.com",
                       "commit", "-qm", "chore: mock regression target"])
    os.environ["DEMO_REPO"] = str(TARGET_REPO)

    (SB2 / ".claude" / "skills").mkdir(parents=True, exist_ok=True)
    shutil.copytree(HARNESS / ".claude" / "skills" / "pto-isa", SB2 / ".claude" / "skills" / "pto-isa")
    for ref in ("known-failures.md", "known-failures.before.md"):
        shutil.copy(KNOWN_BEFORE, SB2 / ".claude" / "skills" / "pto-isa" / "references" / ref)
    (SB2 / "learnings").mkdir(parents=True, exist_ok=True)
    for f in ("recent.md", "promoted.md", "corrections.md"):
        shutil.copy(HARNESS / "learnings" / f, SB2 / "learnings" / f)


# ── steps ───────────────────────────────────────────────────────────────────

def step_run() -> None:
    print("  Running (exit 1 is expected — the mock suite fails one case on purpose):\n")
    print("    python3 -m skill_foundry.workflow.run --config demo/config/demo-suites.json \\")
    print("        --arches demo/config/demo-arches.json --target demo --all-suites --run-id", RUN_ID, "\n")
    _run([sys.executable, "-m", "skill_foundry.workflow.run", "--config", DEMO_CONFIG,
          "--arches", DEMO_ARCHES, "--target", "demo", "--all-suites",
          "--run-id", RUN_ID], check=False)
    print()
    print(f"  ✔ produced {RUN_DIR}/run.json  +  {RUN_DIR}/demo-suite.log (normalized by extract-logs)")


def step_report() -> None:
    _run([sys.executable, "-m", "skill_foundry.workflow.report", "--run", RUN_DIR / "run.json",
          "--out", RUN_DIR / "report"])
    print("\n  Failure as the harness sees it today (no triage knowledge):")
    _grep(RUN_DIR / "report.md", FAIL_CASE)


def step_review() -> None:
    _run([sys.executable, "-m", "skill_foundry.workflow.review", "--run", RUN_DIR / "run.json",
          "--baseline", BASELINE])


def step_teach() -> None:
    print("  (auto-capture) python3 -m skill_foundry.cli.teach records the correction in strict LRN-… format:\n")
    _run([sys.executable, "-m", "skill_foundry.cli.teach",
          f"device vcvt round-field mismatch in {FAIL_CASE} -> known vcvt round-field pattern; annotate instead of re-triage -> promote vcvt round-field swap into known-failures",
          "--file", SB2 / "learnings" / "recent.md"])
    print("\n  (auto-draft alternative) session_digest.py drafts the same entry straight from run.json:")
    _run([sys.executable, "-m", "skill_foundry.lib.session_digest", "--run", RUN_DIR / "run.json",
          "--file", SB2 / "learnings" / "recent.md"], check=False)
    print("\n  Latest pending entry in the sandbox recent.md:")
    text = (SB2 / "learnings" / "recent.md").read_text(encoding="utf-8")
    blocks = text.split("\n## ")
    print("    ## " + blocks[-1].strip().replace("\n", "\n    "))


def step_propose() -> None:
    print("  (auto-propose) promote.py turns the pending entry into a reviewable diff "
          "(no write yet):\n")
    _run([sys.executable, "-m", "skill_foundry.cli.promote", "--root", SB2, "--propose"])


def step_apply() -> None:
    print("  (apply) write the edit into the sandbox known-failures.md:\n")
    _run([sys.executable, "-m", "skill_foundry.cli.promote", "--root", SB2, "--apply", "--no-review"])
    before_txt = (SB2 / ".claude" / "skills" / "pto-isa" / "references" / "known-failures.before.md").read_text(encoding="utf-8")
    after_txt = SB2_KNOWN.read_text(encoding="utf-8")
    n_before = sum(1 for line in before_txt.splitlines() if line.startswith("### ") and "vcvt" in line)
    n_after = sum(1 for line in after_txt.splitlines() if line.startswith("### ") and "vcvt" in line)
    print(f"  Mechanical effect — known-failure signatures go {n_before} → {n_after}:")
    print(f"    before: {n_before} known-failure signatures")
    print(f"    after:  {n_after} known-failure signatures")
    print("\n  learnings/ bookkeeping after apply (promoted + corrections):")
    for line in (SB2 / "learnings" / "promoted.md").read_text(encoding="utf-8").splitlines():
        if "vcvt" in line:
            print(f"    {line.strip()}")


def step_rerun() -> None:
    print("  Re-render the SAME run.json against the improved corpus:\n")
    _run([sys.executable, "-m", "skill_foundry.workflow.report", "--run", RUN_DIR / "run.json",
          "--known", SB2_KNOWN, "--out", RUN_DIR / "report-known"])
    print("\n  Failure line AFTER learning (now annotated as known):")
    _grep(RUN_DIR / "report-known.md", FAIL_CASE)


def step_takeaway() -> None:
    print("""
  Run artifacts:  {run}/run.json, report.md, report-known.md, demo-suite.log
  Sandbox (loop): {sb}

  - USE:      run.py → parse_gtest → build_report → diff_runs
  - IMPROVE:  teach / session_digest.py (capture) →
              promote.py --propose (draft diff) → --apply → annotated next report

  The real targets (pto-isa, pto-vmi) use the same flow with config/suites.json.

  Capture is automated; promotion is always a reviewed diff. The agent didn't get
  smarter — the *harness* did.
""".format(run=RUN_DIR, sb=SANDBOX))


STEPS: list[dict] = [
    dict(key="run", short="run", needs=(), title="Use — run the suite",
         what="One command runs the demo suite through the REAL run.py → run.json + raw log.",
         more="The mock gtest runner is fake, but the driver is the real run.py. "
              "It records the target repo's git ref, dirty flag, host, and env snapshot, "
              "so every result is reproducible — the same metadata the pto-isa runs carry. "
              "In the real flow, --all-suites auto-skips suites whose prereqs are missing "
              "(compiler / CANN headers+simulator / device / MPI); an explicit --suite force-runs.",
         run=step_run),
    dict(key="report", short="report", needs=("run",), title="Use — report (before learning)",
         what="report.py renders the run into report.md/.html — one failing case shows up as a raw FAIL.",
         more="Right now the harness has no triage knowledge: VecOpTest.case_vcvt_bf16fp16_128x128 "
              "is just 'FAIL'. The whole point of the improve loop is to make this line smarter.",
         run=step_report),
    dict(key="review", short="review", needs=("run",), title="Use — review vs the pinned baseline",
         what="review.py diffs the run against demo/baseline/demo-baseline.json — the failing case is flagged as a PASS→FAIL regression.",
         more="Regression = diff vs the PINNED baseline — refresh the baseline only deliberately. "
              "Avg and p99 are both tracked; p99 rising >15% trips a perf flag even when avg is flat — "
              "never report average alone.",
         run=step_review),
    dict(key="teach", short="teach", needs=("review",), title="Improve — auto-capture the correction",
         what="A person says 'that's a known vcvt round-field issue'. The AI logs it automatically (python3 -m skill_foundry.cli.teach) as a strict, parseable LRN-… entry.",
         more="Capture is automatic and append-only: when you correct the agent ('no / actually / remember …'), "
              "it runs ./harness teach by itself and replies with the LRN-… id — one command, strict format, no freeform editing. "
              "session_digest.py can even draft the same entry straight from the run's failures.",
         run=step_teach),
    dict(key="propose", short="propose", needs=("teach",), title="Improve — auto-propose a diff",
         what="promote.py --propose turns the pending entry into a reviewable git-style diff — no write yet.",
         more="This is the automation boundary: propose is automatic (optional review); apply is also automatic "
              "(--pr commits, pushes, and creates the MR). Nothing changes in the shared skills until the MR is "
              "MERGED on the remote — branch protection is the gate.",
         run=step_propose),
    dict(key="apply", short="apply", needs=("propose",), title="Improve — apply + bookkeeping  🟢 AUTO",
         what="--pr applies the edit, commits, pushes, and AUTO-CREATES the MR. You only merge it on the remote (branch protection gates the merge).",
         more="Capture is automatic — recent.md is the harness's own memory, append-only, cheap, revertible. "
              "Apply is now also automatic: --pr applies + commits + pushes + opens the MR (via glab or the GitCode API "
              "with GITCODE_TOKEN). The only human step left is MERGING the MR on the remote — same principle as "
              "Claude Code auto-writing memory, with branch protection as the gate. "
              "RED line: the harness never auto-REMOVES or auto-CHANGES an existing check — it only ADDS.",
         run=step_apply),
    dict(key="rerun", short="rerun", needs=("apply",), title="Improve — re-render with the new knowledge",
         what="Re-render the SAME run.json with the improved corpus → the failure is now annotated as known.",
         more="The agent didn't get smarter — the harness did. Every teammate gets the same improvement via git.",
         run=step_rerun),
    dict(key="takeaway", short="takeaway", needs=(), title="Takeaway",
         what="Summary + where the artifacts landed.",
         more="",
         run=step_takeaway),
]
BY_KEY = {s["key"]: s for s in STEPS}

# What the scripts run for you vs. what needs a human, per step.
ROLES: dict[str, tuple[str, str, str]] = {
    "run": ("python3 -m skill_foundry.workflow.run --target demo --all-suites",
            "runs the suite and normalizes the log into run.json",
            "nothing — press Enter to run"),
    "report": ("python3 -m skill_foundry.workflow.report --run <run.json>",
               "renders report.md + report.html from run.json",
               "nothing — just read the FAIL line"),
    "review": ("python3 -m skill_foundry.workflow.review --run <run.json> --baseline …",
               "diffs vs baseline → regressions / fixes / perf flags",
               "nothing — read which cases regressed"),
    "teach": ("./harness teach \"wrong → correct → action\"",
              "logs a strict LRN-… entry (or the AI auto-runs it when you correct it)",
              "YOUR judgment — decide the correct triage"),
    "propose": ("./harness promote --propose",
                "drafts a git-style diff (writes nothing yet)",
                "nothing — just review the proposed diff"),
    "apply": ("./harness promote --pr",
              "applies + commits + pushes + auto-creates the MR (glab / GITCODE_TOKEN)",
              "merge the MR on the remote (branch protection gates it)"),
    "rerun": ("python3 -m skill_foundry.workflow.report --run <run.json> --known …",
              "re-renders with the new corpus → failure annotated 'known'",
              "nothing — watch the line flip to 'known'"),
    "takeaway": ("—",
                 "—",
                 "decide what to run next (the real suites)"),
}


def run_step(s: dict, done: set[str]) -> None:
    for need in s["needs"]:
        if need not in done:
            print(ui.c(f"  ⚠ prerequisite '{need}' not run yet — running it first.\n", ui.YELLOW))
            run_step(BY_KEY[need], done)
    sys.stdout.flush()
    s["run"]()
    sys.stdout.flush()
    done.add(s["key"])


def _paths(paused: bool = False) -> None:
    msg = "Demo paused." if paused else "Demo finished."
    print(f"\n  {msg} Artifacts:")
    print(f"    run artifacts: {RUN_DIR}")
    print(f"    sandbox:       {SANDBOX}\n")


def _progress(done: set[str]) -> str:
    n = sum(1 for s in STEPS if s["key"] in done)
    width = 22
    filled = round(n / len(STEPS) * width)
    return f"[{'█' * filled}{'░' * (width - filled)}]  {n}/{len(STEPS)}"


def _stepmap(current: int, done: set[str]) -> str:
    parts = []
    for i, s in enumerate(STEPS):
        tag = s["short"]
        if i == current:
            parts.append(ui.c(f"▶{tag}", ui.BOLD))
        elif s["key"] in done:
            parts.append(ui.c(f"✓{tag}", ui.GREEN))
        else:
            parts.append(f"·{tag}")
    return "  ".join(parts)


def _header(idx: int, done: set[str]) -> None:
    s = STEPS[idx]
    print()
    print(ui.c(SEP, ui.BOLD))
    print(ui.c(f"  STEP {idx + 1} / {len(STEPS)}   ·   {s['title']}", ui.BOLD))
    print(ui.c(SEP, ui.BOLD))
    print()
    print(f"  progress  {_progress(done)}")
    print("  steps     " + _stepmap(idx, done))
    print()
    print(ui.c("  What this step does", ui.BOLD))
    for line in textwrap.wrap(s["what"], width=66):
        print(f"    {line}")
    print()
    cmd, auto, human = ROLES.get(s["key"], ("—", "—", "—"))
    print(ui.c("  Who does what", ui.BOLD))
    print(f"    ▸ command   {cmd}")
    print(ui.c(f"    🟢 harness  {auto}", ui.GREEN))
    print(ui.c(f"    🟡 you       {human}", ui.YELLOW))
    print()
    sys.stdout.flush()


def intro() -> None:
    ui.banner("Sandboxed demo — no hardware")
    print("""
  The harness turns "run the regression" into a shared skill + scripts + a
  pinned baseline, and it gets BETTER each time you teach it a correction.

  Two halves, shown step by step:
    1. USE it     — run → report → review  (all through the real drivers)
    2. IMPROVE it — capture → propose → apply → the triage gets smarter

  Each step is framed in its own block with a progress bar and a step map
  (✓ done · ▶ current · · upcoming), plus a "Who does what" box.

  Who does what, automatically:

    🟢 harness — runs on its own: run, extract, report, review, capture (teach),
                 propose (draft a diff), dry-run previews.
    🤖 AI      — auto-captures a correction when you correct it ("no / actually /
                 remember …") and replies with the LRN-… id; triages per the skill.
    🟡 you     — your judgment (the wrong → correct → action content) and merging
                 the MR on the remote (promote --pr auto-creates it).
    🔴 never   — remove or change an existing check (the harness only ADDS).

  The one rule to remember:

    🟢 Auto-APPEND is safe  — the harness logs lessons to its own memory
                              (learnings/recent.md) freely.
    🟡 Auto-EDIT is gated    — --pr auto-applies + pushes + creates the MR; the
                              shared skills change only when you MERGE it on the
                              remote (branch protection).

  Same line Claude Code draws: it auto-writes its memory but never auto-edits
  your CLAUDE.md. A machine that silently rewrites shared knowledge turns its
  own mistakes into everyone's blind spots — a wrong "known failure" would
  hide real regressions.

  The rules that keep the regression signal honest:

    1. The pinned baseline is the ground truth — "regression" = diff vs it.
       Refresh it only deliberately (new suites / arch changes), never casually.
    2. Never auto-remove or auto-change an existing check — the harness adds
       entries; it never silently deletes or weakens one.
    3. p99 > +15% flags a perf regression even if the average looks stable —
       never trust average alone.
    4. An npu-sim suite needs BOTH the CANN compile headers AND the simulator —
       python3 -m skill_foundry.workflow.run --list marks it ! if either is missing.
    5. --all-suites auto-skips missing prereqs; an explicit --suite force-runs.
    6. Every run records context (git ref, dirty flag, host, env), so any
       result is reproducible on another machine.

  After each step you choose what to do: run & continue, skip, go back,
  jump, or explain.
""")


def tour_loop() -> int:
    done: set[str] = set()
    idx = 0
    last = len(STEPS) - 1
    while True:
        s = STEPS[idx]
        _header(idx, done)
        choice = ui.select_menu(
            ui.c("Your move  ·  ↑/↓ choose  ·  Enter confirm  ·  1–6 jump  ·  q quit", ui.BOLD),
            [
                ("▶  run this step & continue", "run"),
                ("⏭  skip to the next step   ", "next"),
                ("⏮  go back one step        ", "prev"),
                ("🗺  jump to any step        ", "jump"),
                ("🛈  explain this step       ", "more"),
                ("✕  quit demo               ", "quit"),
            ],
        )
        if choice == "run":
            print()
            run_step(s, done)
            print(ui.c(f"  ✔ Step {idx + 1} complete — '{s['title']}'", ui.GREEN))
            if idx < last:
                idx += 1
            else:
                _paths(paused=False)
                return 0
        elif choice == "next":
            idx = min(idx + 1, last)
        elif choice == "prev":
            idx = max(idx - 1, 0)
        elif choice == "jump":
            sel = ui.select_menu("Jump to:", [
                (f"{i + 1}. {t['title']}", i) for i, t in enumerate(STEPS)
            ])
            if sel is not None:
                idx = sel
        elif choice == "more":
            print()
            for line in textwrap.wrap(s["more"] or "—", width=66):
                print("  " + line)
            print()
            ui.ask("Press Enter to continue ")
        else:
            _paths(paused=True)
            return 0
    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if "--straight" in args:
        return subprocess.run([str(HARNESS / "demo" / "run_demo.sh")]).returncode
    setup()
    intro()
    if not sys.stdin.isatty():
        # piped / non-interactive: fall back to running each step straight through
        print("(stdin is not a terminal — running all steps straight through)\n")
        done: set[str] = set()
        for i, s in enumerate(STEPS):
            _header(i, done)
            run_step(s, done)
            print()
        return 0
    return tour_loop()


if __name__ == "__main__":
    raise SystemExit(main())
