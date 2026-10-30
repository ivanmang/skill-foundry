#!/usr/bin/env python3
"""tilelangGym SoftLib/ST pack gate — TRACE / Done-bar / Motif / PRC / PR9 / RESULT.

Motif SoftLib T-ladder accepts tip TRACE slash abbrevs (`softlib_simt_T128` / `T256` / `T512`) as well as full tags.

Validates a closed (or in-progress) explore pack directory against the
SoftLib/ST improve-loop contract, without launching multi-hour opencode.

Env:
  TILELANGGYM_PACK   pack directory (required unless --pack)
  TILELANGGYM_PRC    optional PRC knowledge root (default hub/tilelanggym/...)

Usage:
  TILELANGGYM_PACK=demo/fixtures/tilelanggym-pack-ok \\
    python3 -m skill_foundry.lib.tilelanggym_gate --suite sv567-1xg-clean
  python3 -m skill_foundry.lib.tilelanggym_gate --pack PATH --suite sv567-nx1-outer
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from skill_foundry.paths import ROOT

DEFAULT_PRC = ROOT / "hub" / "tilelanggym" / "perf-review-knowledge"
MOTIF_SEED = ROOT / "hub" / "tilelanggym" / "MOTIF_SEED_SV567_absmax.md"

TRACE_REQUIRED_SECTIONS = (
    "Meta",
    "Aims lock",
    "Motif seed",
    "Decision log",
    "Tried",
    "Best-sweep",
    "SEMANTICS_GATE",
    "Coverage COMPARE",
    "What-if",
)

# SoftLib 1×G Motif ladder tags that Coverage COMPARE must mention (name only).
SOFTLIB_1XG_TAGS = (
    "softlib_simt_stock_stream",
    "softlib_simt_wg_lds_matrix",
    "softlib_simt_wc_lds_matrix",
    "softlib_simt_loadall_absall",
    "softlib_simt_dual_drain",
    "softlib_simt_wc_multi",
    "softlib_simt_T128",
    "softlib_simt_T256",
    "softlib_simt_T512",
)

# dual_drain must cover all G — Coverage rows or tags mentioning G64/G128.
DUAL_DRAIN_G = ("G16", "G32", "G64", "G128")

VMI_OUTER_TAGS = (
    "vmi_outer_vmax_fold",
    "vmi_outer_era_absmax_only",
    "vmi_outer_era_case3_recip",
    "vmi_outer_vand_i32",
    "vmi_outer_vand_alternate_builder",
)

RESULT_REQUIRED_COLS = ("era=", "reduce_axis=", "motif")  # flexible: present as headers or column tokens
RESULT_COL_ALIASES = {
    "era=": ("era=", "era", "Era"),
    "reduce_axis=": ("reduce_axis=", "reduce_axis", "axis"),
    "motif": ("motif", "tag", "seed_tag", "schedule_tag"),
}


def _fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)


def resolve_pack(cli_pack: str | None) -> Path:
    raw = cli_pack or os.environ.get("TILELANGGYM_PACK") or ""
    if not raw:
        raise SystemExit(
            "usage: set TILELANGGYM_PACK or pass --pack <pack-dir> "
            "(point at a closed explore pack with TRACE/RESULT/ANALYSIS)"
        )
    p = Path(raw).expanduser().resolve()
    if not p.is_dir():
        raise SystemExit(f"pack not a directory: {p}")
    return p


def find_first(pack: Path, names: tuple[str, ...]) -> Path | None:
    for n in names:
        cand = pack / n
        if cand.is_file():
            return cand
    # shallow search
    for n in names:
        hits = list(pack.rglob(n))
        if hits:
            return hits[0]
    return None


def check_trace(pack: Path, errors: list[str], warnings: list[str]) -> Path | None:
    trace = find_first(pack, ("EXPLORATION_TRACE.md", "exploration_trace.md"))
    if trace is None:
        _fail("EXPLORATION_TRACE.md missing (Done-bar: no DONE without TRACE)", errors)
        return None
    text = trace.read_text(encoding="utf-8", errors="replace")
    missing = [s for s in TRACE_REQUIRED_SECTIONS if s.lower() not in text.lower()]
    if missing:
        _fail(f"TRACE missing sections: {', '.join(missing)}", errors)
    if "Coverage COMPARE" in text or "coverage compare" in text.lower():
        pass
    else:
        _fail("TRACE missing Coverage COMPARE section", errors)
    return trace


def _softlib_tag_present(trace_text: str, tag: str) -> bool:
    """True if full tag appears, or SoftLib T-ladder slash abbrev (tip TRACE form).

    Tip packs (e.g. t788u_r2) write Coverage as:
      `softlib_simt_T128` / `T256` / `T512`
    or softlib_simt_T128 / T256 / T512
    Full tags (fixture) softlib_simt_T256 etc. also PASS.
    """
    if tag in trace_text:
        return True
    # Only T-ladder tags may abbreviate after a softlib_simt_T* prefix on the same line.
    if not tag.startswith("softlib_simt_T") or tag == "softlib_simt_T128":
        # T128 is the anchor — must appear in full (or as softlib_simt_T128) somewhere.
        # For non-T tags, exact match only (handled above).
        if tag.startswith("softlib_simt_T"):
            short = tag[len("softlib_simt_"):]  # T128
            for line in trace_text.splitlines():
                if "softlib_simt_T" in line and short in line:
                    return True
        return False
    short = tag[len("softlib_simt_"):]  # T256 / T512
    for line in trace_text.splitlines():
        if "softlib_simt_T" not in line:
            continue
        # slash-abbrev row: ... T128 / T256 / T512 ...
        if short in line and ("/" in line or f"softlib_simt_{short}" in line):
            return True
    return False


def check_motif_softlib(trace_text: str, errors: list[str]) -> None:
    low = trace_text
    for tag in SOFTLIB_1XG_TAGS:
        if not _softlib_tag_present(low, tag):
            _fail(f"Motif ladder tag missing from TRACE/Coverage: {tag}", errors)
    # require explicit G64 and G128 near dual_drain
    if "G64" not in low or "G128" not in low:
        _fail("Coverage must mention G64 and G128 (dual_drain all-G rule)", errors)
    elif "dual_drain" not in low and "softlib_simt_dual_drain" not in low:
        _fail("Coverage missing softlib_simt_dual_drain", errors)
    if "axis=1xG" not in low and "axis=1×G" not in low and "1xG" not in low:
        _fail("SoftLib SoT cell must declare axis=1xG (Nx1 is appendix)", errors)


def check_motif_outer(trace_text: str, errors: list[str]) -> None:
    for tag in VMI_OUTER_TAGS:
        if tag not in trace_text:
            _fail(f"Outer Motif tag missing from TRACE/Coverage: {tag}", errors)
    if "reduce_axis=outer" not in trace_text and "reduce_axis = outer" not in trace_text:
        # soft: accept 'outer' + 'Nx1'
        if "Nx1" not in trace_text and "N×1" not in trace_text and "outer" not in trace_text.lower():
            _fail("Outer suite TRACE must label reduce_axis=outer / Nx1", errors)
    if "VMAX" not in trace_text and "vmax" not in trace_text:
        _fail("Outer suite must mention pure VMAX (no VC/VCG as reduce)", errors)


def check_pr9(pack: Path, errors: list[str], require_both_arms: bool) -> None:
    pr9 = list(pack.rglob("*_running_ipc_pr9.png"))
    ipc_only = [
        p for p in pack.rglob("*_running_ipc.png")
        if not p.name.endswith("_running_ipc_pr9.png") and "_pr9" not in p.name
    ]
    if require_both_arms:
        if len(pr9) < 2:
            _fail(
                f"Done-bar compare claim needs PR9 *_running_ipc_pr9.png for both arms "
                f"(found {len(pr9)}); IPC-only rejected",
                errors,
            )
    else:
        if not pr9:
            _fail(
                "Missing forced PR9 overlays (*_running_ipc_pr9.png); "
                "IPC-only *_running_ipc.png is FAIL",
                errors,
            )
    # If ipc-only exist without any pr9 → hard fail already; if both, warn via count
    if ipc_only and not pr9:
        _fail(
            "Found IPC-only running_ipc PNGs without _pr9 overlays: "
            + ", ".join(p.name for p in ipc_only[:5]),
            errors,
        )


def check_analysis_prc(pack: Path, errors: list[str]) -> None:
    analysis = find_first(pack, ("ANALYSIS.md", "analysis.md", "ST_ANALYSIS.md"))
    if analysis is None:
        _fail("ANALYSIS.md missing", errors)
        return
    text = analysis.read_text(encoding="utf-8", errors="replace")
    # At least one ready PRC cite when perf narrative present; always require PRC- pattern for gate suites
    cites = re.findall(r"PRC-[A-Z]+-\d{3}", text)
    if not cites:
        _fail("ANALYSIS must cite at least one PRC-id (e.g. PRC-IPC-001 / PRC-SCH-001)", errors)
    if "PRC-IPC-001" not in cites and "running_ipc" in text.lower():
        _fail("IPC/overlay narrative without PRC-IPC-001 cite", errors)


def check_result_tsv(pack: Path, errors: list[str], suite: str) -> None:
    result = find_first(pack, ("RESULT.tsv", "result.tsv", "RESULTS.tsv"))
    if result is None:
        # also accept RESULT.md table
        result_md = find_first(pack, ("RESULT.md", "result.md"))
        if result_md is None:
            _fail("RESULT.tsv (or RESULT.md) missing", errors)
            return
        text = result_md.read_text(encoding="utf-8", errors="replace")
    else:
        text = result.read_text(encoding="utf-8", errors="replace")
    blob = text.lower()
    if "era" not in blob:
        _fail("RESULT must carry era= column/field", errors)
    if "reduce_axis" not in blob and "axis" not in blob:
        _fail("RESULT must carry reduce_axis= / axis field", errors)
    if "motif" not in blob and "tag" not in blob:
        _fail("RESULT must carry motif/tag field", errors)
    if suite == "sv567-1xg-clean":
        if "1xg" not in blob and "1×g" not in blob and "inner" not in blob:
            # soft requirement
            pass
    if suite == "sv567-nx1-outer":
        if "outer" not in blob and "nx1" not in blob:
            _fail("Outer suite RESULT rows should label reduce_axis=outer / Nx1", errors)


def check_done_bar(pack: Path, errors: list[str], suite: str) -> None:
    """Done-bar: if TRACE claims DONE / MB_STATUS DONE, enforce full checklist."""
    trace = find_first(pack, ("EXPLORATION_TRACE.md", "exploration_trace.md"))
    if trace is None:
        return
    text = trace.read_text(encoding="utf-8", errors="replace")
    claims_done = bool(
        re.search(r"MB_STATUS\s*[:=]\s*DONE", text, re.I)
        or re.search(r"\bANALYSIS\s+DONE\b", text, re.I)
        or re.search(r"SoftLib SIMT DONE", text, re.I)
        or re.search(r"best-sweep DONE", text, re.I)
    )
    if not claims_done:
        return
    # already collecting errors from other checks; add explicit Done-bar note if PR9 weak
    pr9 = list(pack.rglob("*_running_ipc_pr9.png"))
    if suite.startswith("sv567") and len(pr9) < 1:
        _fail("Done-bar: TRACE claims DONE but no *_running_ipc_pr9.png present", errors)


def check_prc_index(errors: list[str]) -> None:
    prc = Path(os.environ.get("TILELANGGYM_PRC") or DEFAULT_PRC).expanduser()
    script = ROOT / "scripts" / "check_prc_index.py"
    if not script.is_file():
        _fail(f"PRC gate script missing: {script}", errors)
        return
    import subprocess

    env = os.environ.copy()
    env["TILELANGGYM_PRC"] = str(prc)
    r = subprocess.run(
        [sys.executable, str(script), "--knowledge", str(prc)],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        _fail("PRC index gate failed:\n" + (r.stdout + r.stderr)[-800:], errors)


def run_suite(pack: Path, suite: str) -> int:
    errors: list[str] = []
    warnings: list[str] = []
    print(f"tilelangGym gate suite={suite}")
    print(f"pack={pack}")

    trace = check_trace(pack, errors, warnings)
    trace_text = trace.read_text(encoding="utf-8", errors="replace") if trace else ""

    if suite == "sv567-1xg-clean":
        if trace_text:
            check_motif_softlib(trace_text, errors)
        check_pr9(pack, errors, require_both_arms=True)
    elif suite == "sv567-nx1-outer":
        if trace_text:
            check_motif_outer(trace_text, errors)
        check_pr9(pack, errors, require_both_arms=False)
    else:
        _fail(f"unknown suite: {suite}", errors)

    check_analysis_prc(pack, errors)
    check_result_tsv(pack, errors, suite)
    check_done_bar(pack, errors, suite)
    check_prc_index(errors)

    # Motif seed file must exist in hub (contract doc)
    if not MOTIF_SEED.is_file():
        _fail(f"hub Motif seed missing: {MOTIF_SEED}", errors)

    for w in warnings:
        print(f"WARN: {w}")
    if errors:
        print(f"FAIL ({len(errors)}):")
        for e in errors:
            for line in e.splitlines() or [e]:
                print(f"  ✗ {line}")
        return 1
    print("PASS")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="tilelangGym SoftLib/ST pack gate")
    ap.add_argument("--pack", default=None, help="Pack dir (else TILELANGGYM_PACK)")
    ap.add_argument(
        "--suite",
        required=True,
        choices=("sv567-1xg-clean", "sv567-nx1-outer"),
        help="Gate suite name (matches config/suites.json)",
    )
    args = ap.parse_args(argv)
    pack = resolve_pack(args.pack)
    return run_suite(pack, args.suite)


if __name__ == "__main__":
    sys.exit(main())
