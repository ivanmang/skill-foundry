#!/usr/bin/env python3
"""Per-block column statistics for unpacked NPU profiling CSVs.

Deterministically implements SKILL.md §3.1 (min/median/max/mean, tail-block and
dispersion detection, NA handling, pipe-ratio sum check, frequency and
active_bw cross-checks) so the report quotes these numbers instead of
recomputing them by hand.

Usage: summarize_tables.py <unpacked_dir> [csv_name ...]
       (no csv_name -> every *.csv in the directory, sorted)
"""

import csv
import sys
from pathlib import Path
from statistics import mean, median

TAIL_RATIO = 0.6        # last block < median x 0.60 and global min -> tail_block
DISPERSION = 1.10       # max/min above this -> block imbalance flag
RATIO_SUM_TOL = 0.05    # pipe-ratio sum deviating from 1 by more -> suspicious

DISPERSION_MARKERS = ("time", "ratio", "bw(", "datas(")  # *_rate columns excluded
ADDITIVE_MARKERS = ("bw(", "datas(", "instructions", "instr_number",
                    "_hit", "_miss", "_victim")
TIME_COLUMNS = ("aiv_time(us)", "aic_time(us)")
PIPE_RATIO_SETS = (
    ("aic", ("aic_cube_ratio", "aic_scalar_ratio", "aic_mte1_ratio",
             "aic_mte2_ratio", "aic_mte3_ratio", "aic_fixpipe_ratio")),
    ("aiv", ("aiv_vec_ratio", "aiv_scalar_ratio",
             "aiv_mte2_ratio", "aiv_mte3_ratio")),
)


def fmt(value):
    if value == int(value):
        return str(int(value))
    return "{:.6g}".format(value)


def parse_number(raw):
    text = (raw or "").strip()
    if text in ("", "NA"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = [name.strip() for name in next(reader)]
        rows = [row for row in reader if any((cell or "").strip() for cell in row)]
    # Drop trailing empty-name columns produced by CSV trailing commas.
    keep = len(header)
    while keep > 0 and header[keep - 1] == "":
        keep -= 1
    header = header[:keep]
    rows = [row[:keep] for row in rows]
    return header, rows


def block_sort_key(row, header):
    try:
        return (float(row[header.index("block_id")]), 0)
    except (ValueError, IndexError):
        return (float("inf"), 1)


def block_label(row, header):
    try:
        return "b" + str(int(float(row[header.index("block_id")])))
    except (ValueError, IndexError):
        return "?"


def is_rate(name):
    return "rate" in name


def is_additive(name):
    return not is_rate(name) and any(marker in name for marker in ADDITIVE_MARKERS)


def is_dispersion_eligible(name):
    return not is_rate(name) and any(marker in name for marker in DISPERSION_MARKERS)


def extract_columns(header, rows):
    """Return {column_name: [float|None per row]} preserving header order."""
    columns = {}
    order = []
    for index, name in enumerate(header):
        if name in ("block_id", "sub_block_id") or name in columns:
            continue
        columns[name] = [parse_number(row[index]) if index < len(row) else None
                         for row in rows]
        order.append(name)
    return columns, order


def detect_tail(columns, block_count):
    """Return (column_name, index) of a tail block, or None."""
    for name in TIME_COLUMNS:
        values = columns.get(name)
        if not values or len(values) < 2 or any(v is None for v in values):
            continue
        med = median(values)
        last = values[-1]
        if last < TAIL_RATIO * med and last == min(values):
            return name, len(values) - 1
    return None


def print_column_stats(name, values, block_ids, tail_index):
    numbers = [v for v in values if v is not None]
    if all(v == 0 for v in numbers):
        print("  {}: 全 0（真实零，有效结论）".format(name))
        return
    if len(set(numbers)) == 1:
        print("  {}: 恒定 {}".format(name, fmt(numbers[0])))
        return
    pairs = [(v, block_ids[i]) for i, v in enumerate(values) if v is not None]
    low, low_block = min(pairs, key=lambda item: item[0])
    high, high_block = max(pairs, key=lambda item: item[0])
    line = "  {}: med {} / min {} ({}) / max {} ({}) / mean {}".format(
        name, fmt(median(numbers)), fmt(low), low_block,
        fmt(high), high_block, fmt(mean(numbers)))
    if is_additive(name):
        line += " | Σ {}".format(fmt(sum(numbers)))
    if is_dispersion_eligible(name) and low > 0:
        ratio = high / low
        line += " | max/min={:.3g}".format(ratio)
        if ratio > DISPERSION:
            line += " ⚠离散度>1.10"
        if tail_index is not None and len(numbers) > 2:
            kept = [v for i, v in enumerate(values)
                    if v is not None and i != tail_index]
            if kept and min(kept) > 0:
                kept_ratio = max(kept) / min(kept)
                line += "（剔tail={:.3g}{})".format(
                    kept_ratio, " ⚠" if kept_ratio > DISPERSION else "")
    print(line)


def print_ratio_sum_check(columns, row_count):
    for prefix, pipe_names in PIPE_RATIO_SETS:
        if not all(name in columns for name in pipe_names):
            continue
        sums = []
        for i in range(row_count):
            row_values = [columns[name][i] for name in pipe_names]
            if any(v is None for v in row_values):
                continue
            sums.append(sum(row_values))
        if not sums:
            continue
        low, high = min(sums), max(sums)
        ok = abs(low - 1) <= RATIO_SUM_TOL and abs(high - 1) <= RATIO_SUM_TOL
        print("  ratio 和校验: {} ∈ [{:.6g}, {:.6g}] {}".format(
            "+".join(name.split("_", 1)[1] for name in pipe_names),
            low, high, "✓" if ok else "⚠和偏离 1，分片口径可疑"))


def summarize_file(path, shared_signatures):
    header, rows = read_csv(path)
    if not rows:
        print("== {}（空表）".format(path.name))
        print()
        return {}
    rows.sort(key=lambda row: block_sort_key(row, header))
    block_ids = [block_label(row, header) for row in rows]
    columns, order = extract_columns(header, rows)
    print("== {}（{} blocks）".format(path.name, len(rows)))

    # Time/cycles columns identical to an earlier table: skip the repetition.
    # (all-NA columns excluded -- they are already covered by the 全 NA section)
    time_names = [n for n in TIME_COLUMNS if n in columns] + ["aiv_total_cycles",
                                                              "aic_total_cycles"]
    skipped = []  # list, not set: keeps header order, output stays deterministic
    for name in time_names:
        values = columns.get(name)
        if values is None or all(v is None for v in values):
            continue
        signature = (name, tuple(values))
        if signature in shared_signatures:
            skipped.append(name)
    order = [name for name in order if name not in skipped]
    tail = detect_tail(columns, len(rows))
    tail_index = tail[1] if tail else None
    tail_printed = False

    all_na = []
    for name in order:
        values = columns[name]
        if all(v is None for v in values):
            all_na.append(name)
            continue
        print_column_stats(name, values, block_ids, tail_index)
    for name in skipped:
        print("  {}: 与前表逐 block 一致（略）".format(name))

    if all_na:
        aic_na = [n for n in all_na if n.startswith("aic_")]
        others = [n for n in all_na if not n.startswith("aic_")]
        if aic_na:
            print("  全 NA 列: aic_* ×{} → 本算子未使用 Cube 核（AI Core 为 Vector 型）"
                  .format(len(aic_na)))
        if others:
            print("  全 NA 列: {}".format(", ".join(others)))

    if tail:
        name, index = tail
        med = median(columns[name])
        # Same time column as an earlier table -> same tail, print once.
        if (name, tuple(columns[name])) not in shared_signatures:
            print("  tail_block: {} 末块 {} = {} < med×60% = {} 且为全表最小 "
                  "→ tail_block（总元素数不整除 block 数；其 ratio 不可与全量 block 直接比较）"
                  .format(name, block_ids[index], fmt(columns[name][index]),
                          fmt(TAIL_RATIO * med)))
            tail_printed = True
    if not tail_printed:
        for name in TIME_COLUMNS:
            if (name, tuple(columns.get(name, []))) in shared_signatures:
                print("  tail_block: 同前表（{}），本表不重复检测".format(name))
                break

    print_ratio_sum_check(columns, len(rows))
    print()

    for name in time_names:
        values = columns.get(name)
        if values is not None:
            shared_signatures.add((name, tuple(values)))
    return columns


def print_cross_checks(table_columns):
    """Frequency check, active_bw whole-run averages, cross-table consistency."""
    print("== 交叉验证")
    lines = []
    for table_name, columns in table_columns.items():
        times = columns.get("aiv_time(us)") or columns.get("aic_time(us)")
        cycles = columns.get("aiv_total_cycles") or columns.get("aic_total_cycles")
        if times and cycles and all(t and c for t, c in zip(times, cycles)):
            freq = median([c / t for t, c in zip(times, cycles)])
            lines.append("  cycles/μs = {:.6g} ≈ 主频（{}，不一致则数据可疑）".format(
                freq, table_name))
            break
    derived = set()
    for columns in table_columns.values():
        for name in columns:
            if not name.endswith("_active_bw(GB/s)"):
                continue
            ratio_name = name[:-len("_active_bw(GB/s)")] + "_ratio"
            if ratio_name not in columns:
                continue
            products = [bw * ratio for bw, ratio in zip(columns[name],
                                                        columns[ratio_name])
                        if bw is not None and ratio is not None]
            if products:
                derived.add("  {}: 全程平均bw ≈ active_bw×ratio ≈ {} GB/s（推算）".format(
                    name[:-len("_active_bw(GB/s)")], fmt(median(products))))
    lines.extend(sorted(derived))
    shared = {}
    for table_name, columns in table_columns.items():
        for name, values in columns.items():
            if any(v is not None for v in values):
                shared.setdefault(name, []).append((table_name, tuple(values)))
    for name, occurrences in sorted(shared.items()):
        if len(occurrences) < 2:
            continue
        tables = [t for t, _ in occurrences]
        if all(v == occurrences[0][1] for _, v in occurrences):
            lines.append("  {}: {} 各表逐 block 一致 ✓".format(name, "/".join(tables)))
        else:
            lines.append("  {}: ⚠{} 各表不一致，数据可疑".format(name, "/".join(tables)))
    for line in lines:
        print(line)


def main():
    if len(sys.argv) < 2:
        print("Usage: summarize_tables.py <unpacked_dir> [csv_name ...]")
        return 1
    root = Path(sys.argv[1])
    if len(sys.argv) > 2:
        paths = [Path(arg) for arg in sys.argv[2:]]
    else:
        paths = sorted(root.glob("*.csv"))
    if not paths:
        print("no CSV files found in {}".format(root))
        return 1
    shared_signatures = set()
    table_columns = {}
    for path in paths:
        if not path.is_file():
            print("!! 缺文件: {}".format(path))
            continue
        columns = summarize_file(path, shared_signatures)
        if columns:
            table_columns[path.name] = columns
    if table_columns:
        print_cross_checks(table_columns)
    return 0


if __name__ == "__main__":
    sys.exit(main())
