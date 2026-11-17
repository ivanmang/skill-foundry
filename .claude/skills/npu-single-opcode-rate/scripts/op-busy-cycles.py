#!/usr/bin/env python3
# Busy cycles for one opcode, from a paired instruction trace.
#
# Implements the reading rules in tilelang/techniques/single-opcode-rate.md:
#   - veccore0 only (core == 0, sub == 1)
#   - pair each instruction by PC and ID across the two dumps:
#     *.instr_popped_log.dump holds the START (issue) of each instruction
#     (is_popped == 1); *.instr_log.dump holds its COMPLETION (is_popped == 0)
#   - active cycles of one instruction are completion - issue + 1,
#     both ticks included
#   - the reported busy time is the union of the per-warp [issue, completion]
#     windows, inclusive: an overlapped tick is counted once, never
#     double-counted (warp 0 running 45..60 and warp 1 running 56..74 is
#     74-45+1, not (60-45+1)+(74-56+1)); the span is kept as a secondary
#     number
#
# Usage:
#   python3 op-busy-cycles.py OPNAME instr_popped_log instr_log
#
# OPNAME is the opcode to account, e.g. SIMT_LDS. The two arguments are the
# two dumps of the same recorded launch: the popped log (starts) first, the
# instruction log (completions) second. When the recorder writes one
# instr.bin holding both halves, pass that file twice. Two arguments are
# required even then: the point is that the agent must name both halves of
# the pair before any number is printed.
#
# Output:
#   op=   the opcode asked for
#   n=    paired instructions (warp issues)
#   span= last completion minus first issue (bunched warps make this too big)
#   busy= union of [issue, completion] windows (the rate denominator)
#   act_min / act_med / act_max = per-instruction active-time percentiles
#   unre= issued instructions with no completion partner (truncated trace)
#
# Requires the simulator's decoder module on the import path. Under the
# simulator environment, import the camodel runtime first (see
# tilelang/run/ascend.md, "Launch"); the decoder reads the same install.
import re
import sys

try:
    from cannsim.core.public.instr_decoder import decode_instr_logs_from_file
except ImportError:
    sys.exit(
        "cannot import the trace decoder (cannsim...). Load the simulator "
        "environment first; see tilelang/run/ascend.md, 'Launch'."
    )

ROW = re.compile(r"\(ID:\s*(\d+)\)\s+([A-Z0-9_]+)")


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit("usage: op-busy-cycles.py OPNAME instr_popped_log instr_log")
    opname, popped_path, done_path = sys.argv[1], sys.argv[2], sys.argv[3]

    starts: dict = {}  # from the popped log: is_popped == 1 is the start tick
    dones: dict = {}  # from the instruction log: is_popped == 0 is the completion tick
    for path, popped_flag, table in (
        (popped_path, 1, starts),
        (done_path, 0, dones),
    ):
        for e in decode_instr_logs_from_file(path):
            if e.core != 0 or e.sub != 1 or e.is_popped != popped_flag:
                continue
            m = ROW.search(e.dec or "")
            if not m:
                continue
            key = (e.pc, int(m.group(1)), m.group(2))
            if key not in table:
                table[key] = e.time

    paired = sorted(
        (starts[k], dones[k]) for k in starts if k[2] == opname and k in dones
    )
    unre = sum(1 for k in starts if k[2] == opname and k not in dones)
    if not paired:
        sys.exit(f"no completed {opname} found on veccore0 in either log")

    # union of the per-warp windows, both ticks included:
    # each interval [s, d] covers d - s + 1 ticks, overlaps counted once
    merged = []
    start, end = paired[0]
    for s, d in paired[1:]:
        if s <= end:
            end = max(end, d)
        else:
            merged.append((start, end))
            start, end = s, d
    merged.append((start, end))
    busy = sum(e - s + 1 for s, e in merged)

    acts = sorted(d - s + 1 for s, d in paired)
    span = paired[-1][1] - paired[0][0]
    print(f"assumed veccore0, paired by (pc, id); {len(starts)} issues seen")
    print(
        f"op={opname} n={len(paired)} span={span} busy={busy} "
        f"act_min={acts[0]} act_med={acts[len(acts) // 2]} act_max={acts[-1]} "
        f"unre={unre}"
    )
    print("merged intervals:", merged)


if __name__ == "__main__":
    main()
