#!/usr/bin/env python3
# Instruction rows plus the IPC line, from one instr.bin.
#
# Implements the figure rules in visualization/instr-ipc.md:
#   - veccore0 only (core == 0, sub == 1)
#   - the window is one VF launch, inclusive of both end ticks: start of VF
#     (SIMD) or VF_SIMT (SIMT) from the popped events (is_popped == 1) to its
#     completion from the instruction log (is_popped == 0), completion -
#     start + 1; the VF opcode is not a row and not an IPC issue
#   - opcode rows (default): one row per opcode found in the window, busiest
#     first, one mark per issue
#   - warp rows (--warps, SIMT only): one row per warp, marks colored by
#     opcode, address ops gray. instr.bin has no warp id; the warp index is
#     inferred only when every body PC issues exactly n_warps times in the
#     window (fully unrolled, one pass): the k-th issue of a PC in tick order
#     belongs to warp k. Once-per-kernel setup/teardown PCs (one issue for the
#     whole VF) stay off the warp rows but count in the IPC line. Any other
#     per-PC count refuses the chart: a loop body that runs several
#     iterations per warp cannot be assigned, and no guess is drawn.
#   - the drawn x-axis ends at the last body issue (span = last_issue + 1).
#     Empty VF drain after the last issue is not drawn — the full VF length
#     is still reported for context, but the chart does not pad empty ticks
#   - the IPC line bins every issue in that drawn span (VF excluded): a point
#     is the bin's issue count over the bin width, drawn at the bin center;
#     the last bin keeps only the ticks that remain
#   - the scalar IPC is issues in the VF window over VF ticks, independent of
#     the drawn span and of the bin
#
# Usage:
#   python3 instr-ipc-plot.py instr.bin simd|simt out.png [--bin W] [--warps] [--vf N]
#
# --bin is the bin width in ticks, default 20 (the width the ST spine uses).
# --warps draws the warp-row variant; it needs simt and refuses simd.
# --vf N selects the N-th VF launch (0-based). Default: require exactly one VF.
#   Use --vf 1 for a warm second launch (tilelang/techniques/i-cache-stall.md).
# Output: one line per row label with its issue count, then
#   VF <ticks>  span <span>  issues <n>  IPC <scalar>  -> <out.png>
#
# matplotlib and the simulator's decoder must be importable; see
# tilelang/run/ascend.md or cce/run/ascend.md for the environment.
import argparse
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

try:
    from cannsim.core.public.instr_decoder import decode_instr_logs_from_file
except ImportError:
    cann = os.environ.get("CANN_PYTHON_PACKAGES")
    if cann:
        sys.path.insert(0, cann)
    try:
        from cannsim.core.public.instr_decoder import decode_instr_logs_from_file
    except ImportError:
        sys.exit(
            "cannot import the trace decoder (cannsim...). Load the simulator "
            "environment, or point CANN_PYTHON_PACKAGES at the CANN python "
            "site-packages; see tilelang/run/ascend.md, 'Pieces'."
        )

ROW = re.compile(r"\(ID:\s*(\d+)\)\s+([A-Z0-9_]+)")
PCRE = re.compile(r"PC: (0x[0-9a-f]+)")
PALETTE = [
    "#1f4e79",
    "#8fb4d4",
    "#1a7a7a",
    "#e07a1f",
    "#1b5e20",
    "#7cb342",
    "#5c4e78",
    "#c45c26",
    "#3d5a80",
    "#6b4c7a",
    "#b5b5b5",
    "#888888",
]
# Address math and control stay gray on warp rows; they belong to no opcode.
COLOR_SKIP = {
    "IADD_I",
    "IADD",
    "LEA",
    "IMAD",
    "S2R",
    "SHFI",
    "MOV",
    "MOVI",
    "BRANCH",
    "ISETP_I",
    "STK",
    "LDK",
    "END",
    "END_LABEL",
    "CALL",
}
GRAY = "#b5b5b5"


def opcode(dec: str):
    m = ROW.search(dec or "")
    return m.group(2) if m else None


def fields(dec: str):
    m = ROW.search(dec or "")
    p = PCRE.search(dec or "")
    return (m.group(2) if m else None), (p.group(1) if p else None)


def window(path: str, kind: str, vf_index: int = 0):
    """One VF launch on veccore0: (VF ticks, start, end, entries, vf_name, n).

    VF ticks = completion - start + 1: both ticks included. The start comes
    from the popped log (is_popped == 1), the completion from the
    instruction log (is_popped == 0) — the general rule in
    visualization/instr-ipc.md and tilelang/techniques/single-opcode-rate.md.
    """
    vf_name = "VF_SIMT" if kind == "simt" else "VF"
    rows = [
        r for r in decode_instr_logs_from_file(Path(path)) if r.core == 0 and r.sub == 1
    ]
    issues = [r.time for r in rows if r.is_popped == 1 and opcode(r.dec) == vf_name]
    dones = [r.time for r in rows if r.is_popped == 0 and opcode(r.dec) == vf_name]
    if not issues:
        sys.exit(f"no {vf_name} issue on veccore0 in {path}")
    if not dones:
        sys.exit(
            f"{vf_name} issues without a completion in {path}: the trace is "
            f"truncated. Pairing and the unre count: tools/op-busy-cycles.py."
        )
    if len(issues) != len(dones):
        sys.exit(
            f"{len(issues)} {vf_name} issues vs {len(dones)} completions in {path}"
        )
    if vf_index < 0 or vf_index >= len(issues):
        sys.exit(
            f"--vf {vf_index} out of range: trace has {len(issues)} {vf_name} launch(es)"
        )
    issue, done = issues[vf_index], dones[vf_index]
    return done - issue + 1, issue, done, rows, vf_name, len(issues)


def collect_ops(rows, vf_name, issue, done):
    ops = []
    for r in rows:
        if r.is_popped != 1:
            continue
        op = opcode(r.dec)
        if op is None or op == vf_name:
            continue
        if issue <= r.time <= done:
            ops.append((r.time - issue, op))
    return ops


def rows_from(ops):
    """One row per opcode in the window, busiest first. Grouping is a later edit."""
    counts = Counter(op for _, op in ops)
    rows = []
    for i, op in enumerate(sorted(counts, key=lambda name: (-counts[name], name))):
        label = op.removeprefix("RV_").removeprefix("SIMT_")
        rows.append((label, {op}, PALETTE[i % len(PALETTE)]))
    return rows


def warp_rows(rows, vf_name, issue, done):
    """Warp assignment plus the once-per-kernel PCs, or a refusal."""
    per_pc = defaultdict(list)
    for r in rows:
        if r.is_popped != 1 or not (issue <= r.time <= done):
            continue
        op, pc = fields(r.dec)
        if op in (None, vf_name):
            continue
        per_pc[pc].append((r.time - issue, op))

    # Mode of per-PC issue counts, ignoring once-per-kernel setup/teardown PCs
    # (for example MOV_XD_IMM / DCCI / END / END_LABEL issue once for the VF).
    counts_pc = Counter(len(v) for v in per_pc.values() if len(v) != 1)
    if not counts_pc:
        sys.exit("REFUSE: no per-warp PCs found in the window.")
    n_warps = max(counts_pc.items(), key=lambda kv: kv[1])[0]
    once = {pc: v[0] for pc, v in per_pc.items() if len(v) == 1}
    bad = {pc: len(v) for pc, v in per_pc.items() if len(v) not in (1, n_warps)}
    if bad:
        sys.exit(
            f"REFUSE: {len(bad)}/{len(per_pc)} PCs do not issue {n_warps} times "
            f"(e.g. {dict(list(bad.items())[:3])}). Warp inference is unsafe "
            "here; the body is not one unrolled pass per warp."
        )
    if once:
        print(
            f"note: {len(once)} once-per-kernel PC(s) stay off the warp rows, counted in IPC"
        )

    events = []  # (tick, warp, op)
    for pc, seq in per_pc.items():
        if len(seq) == 1:
            continue
        seq.sort()
        for k, (t, op) in enumerate(seq):
            events.append((t, k, op))
    events.sort()
    return n_warps, events, list(once.values())


def ipc_line(issues_list, ticks, width):
    n = (ticks + width - 1) // width
    counts = [0] * n
    for t in issues_list:
        if 0 <= t < ticks:
            counts[t // width] += 1
    xs, ys = [], []
    for i, c in enumerate(counts):
        lo, hi = i * width, min(ticks, (i + 1) * width)
        w = hi - lo
        xs.append(lo + w / 2)
        ys.append(c / w)
    return xs, ys


def draw_span(issues_list):
    """X-axis length: last body issue + 1. Empty VF drain is not drawn."""
    last = max(issues_list, default=0)
    return last + 1


def draw(rows, vf_ticks, ops, title, out, width, warps=False, ticks_list=None):
    # ops is (tick, opcode) pairs on opcode rows; ticks_list is the plain tick
    # list (warp rows: body ticks + once-per-kernel ticks) for the IPC line.
    # Drawn span ends at the last issue; vf_ticks is the full VF length (context).
    if warps:
        n_warps, events, opcolors = rows
        issues_list = ticks_list
    else:
        n_warps = len(rows)
        issues_list = [t for t, _ in ops]
    span = draw_span(issues_list)
    figsize_h = (0.30 if warps else 0.34) * n_warps + 2.1
    left = 0.09 if warps else 0.12
    fig = plt.figure(figsize=(10.6, figsize_h), dpi=200, facecolor="white")
    fig.suptitle(title, x=0.01, ha="left", y=0.98, fontsize=13, fontweight="semibold")
    gs = GridSpec(
        2,
        1,
        figure=fig,
        height_ratios=[2.15, 0.95],
        hspace=0.08,
        top=0.88,
        bottom=0.12,
        left=left,
        right=0.97 if warps else 0.90,
    )
    top, bot = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])

    for w in range(n_warps):
        top.axhspan(
            w - 0.5, w + 0.5, color="#f7f8f9" if w % 2 == 0 else "white", linewidth=0
        )
    if warps:
        for t, w, op in events:
            top.vlines(t, w - 0.34, w + 0.34, color=opcolors[op], linewidth=0.7)
        top.set_yticks(range(n_warps), [f"w{w}" for w in range(n_warps)])
    else:
        for i, (label, names, color) in enumerate(rows):
            y = n_warps - 1 - i
            ts = [t for t, op in ops if op in names]
            top.vlines(ts, y - 0.34, y + 0.34, color=color, linewidth=0.7)
            top.text(
                span * 1.015,
                y,
                f"×{len(ts)}",
                va="center",
                ha="left",
                fontsize=8.5,
                color="#444",
                clip_on=False,
            )
        top.set_yticks(range(n_warps), [r[0] for r in reversed(rows)])
    top.set_xlim(0, span)
    top.set_ylim(-0.55, n_warps - 0.45)
    top.tick_params(axis="x", labelbottom=False, length=0)

    xs, ys = ipc_line(issues_list, span, width)
    bot.fill_between(xs, ys, color="#5c4e78", alpha=0.14, linewidth=0)
    bot.plot(xs, ys, color="#5c4e78", linewidth=1.15)
    bot.set_xlim(0, span)
    bot.set_ylim(0, max(4, (max(ys) if ys else 0) + 0.4))
    bot.set_ylabel("IPC")
    bot.set_xlabel("tick (to last issue)")
    bot.yaxis.grid(True, color="#eef0f2", linewidth=0.7)
    bot.set_axisbelow(True)
    if warps:
        handles = [plt.Line2D([], [], color=opcolors[o], linewidth=2) for o in opcolors]
        bot.legend(
            handles,
            list(opcolors),
            fontsize=6,
            ncol=5,
            loc="upper right",
            frameon=False,
        )
    for ax in (top, bot):
        ax.tick_params(length=0, labelsize=9)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    fig.savefig(out, dpi=200, bbox_inches="tight", pad_inches=0.08)
    n = len(issues_list)
    if warps:
        print(
            f"VF {vf_ticks}  span {span}  warps {n_warps}  issues {n}  IPC {n / vf_ticks:.2f}  -> {out}"
        )
    else:
        print(
            f"VF {vf_ticks}  span {span}  issues {n}  IPC {n / vf_ticks:.2f}  -> {out}"
        )


def color_map(events):
    counts = Counter(op for _, _, op in events)
    opcolors = {}
    ci = 0
    for op in sorted(counts, key=lambda n: -counts[n]):
        if op in COLOR_SKIP:
            opcolors[op] = GRAY
        else:
            opcolors[op] = PALETTE[ci % len(PALETTE)]
            ci += 1
    return opcolors


def main(argv):
    p = argparse.ArgumentParser(
        description="Instruction rows plus the IPC line, from one instr.bin."
    )
    p.add_argument("instr")
    p.add_argument("kind", choices=("simd", "simt"))
    p.add_argument("out")
    p.add_argument(
        "--bin", type=int, default=20, help="IPC bin width in ticks (default 20)"
    )
    p.add_argument(
        "--warps",
        action="store_true",
        help="warp rows instead of opcode rows (simt only)",
    )
    p.add_argument(
        "--vf",
        type=int,
        default=None,
        metavar="N",
        help="0-based VF launch index (default 0; use 1 for warm 2nd launch)",
    )
    args = p.parse_args(argv[1:])
    if args.bin < 1:
        p.error("--bin must be a positive number of ticks")
    if args.warps and args.kind != "simt":
        p.error("--warps needs a simt trace: warp ids only exist on VF_SIMT")
    if args.vf is not None and args.vf < 0:
        p.error("--vf must be >= 0")

    vf_index = 0 if args.vf is None else args.vf
    vf_ticks, issue, done, rows, vf_name, n_vf = window(args.instr, args.kind, vf_index)
    if args.vf is None and n_vf > 1:
        sys.exit(
            f"{n_vf} {vf_name} launches in {args.instr}; pass --vf N to pick one "
            f"(warm rates/charts: --vf 1). See tilelang/techniques/i-cache-stall.md."
        )
    ops = collect_ops(rows, vf_name, issue, done)
    vf_tag = f"VF[{vf_index}]" if n_vf > 1 else "VF"
    if args.warps:
        n_warps, events, extra = warp_rows(rows, vf_name, issue, done)
        all_ticks = [t for t, _ in ops] + [t for t, _ in extra]
        span = draw_span(all_ticks)
        draw(
            (n_warps, events, color_map(events)),
            vf_ticks,
            ops,
            f"{args.kind.upper()} warps  ·  {n_warps} warps  ·  span {span} ({vf_tag} {vf_ticks})",
            args.out,
            args.bin,
            warps=True,
            ticks_list=all_ticks,
        )
    else:
        row_list = rows_from(ops)
        for label, names, _ in row_list:
            print(f"{label} {sum(op in names for _, op in ops)}")
        span = draw_span([t for t, _ in ops])
        draw(
            row_list,
            vf_ticks,
            ops,
            f"{args.kind.upper()} instructions  ·  span {span} ({vf_tag} {vf_ticks})",
            args.out,
            args.bin,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
