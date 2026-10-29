#!/usr/bin/env python3
"""Detect which pto-isa arch a given CANN toolkit can compile for and simulate.

Usage:
  ./harness cann                 # analyze ASCEND_HOME_PATH, then scan ~/Ascend
  ./harness cann --home /path/to/cann-9.1.0
  ./harness cann --scan          # scan ~/Ascend and /usr/local/Ascend
  ./harness cann --json

Basis:
  - headers: include/pto/npu/<arch>  -> which arches the toolkit compiles for
  - simulator: tools/simulator/<soc> -> which SoCs it can simulate
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[2]
CONFIG = HARNESS / "config" / "cann.json"


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def version_of(root: Path) -> str:
    for rel in ("compiler/version.info", "opp/version.info", "version.cfg"):
        p = root / rel
        if p.exists():
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("Version="):
                    return line.split("=", 1)[1].strip()
    return "unknown"


def header_arches(root: Path, cfg: dict) -> list[str]:
    npu = root / "include" / "pto" / "npu"
    if not npu.exists():
        return []
    mapping = cfg.get("header_dir_to_arch", {})
    out = []
    for d in sorted(p.name for p in npu.iterdir() if p.is_dir()):
        if d in mapping:
            out.append(mapping[d])
    return sorted(set(out))


def sim_arches(root: Path, cfg: dict) -> list[str]:
    soc2arch = cfg.get("soc_to_arch", {})
    found: list[str] = []
    for base in (root / "x86_64-linux" / "simulator", root / "tools" / "simulator"):
        if not base.exists():
            continue
        for d in sorted(p.name for p in base.iterdir() if p.is_dir()):
            if d in ("common", "bin"):
                continue
            a = soc2arch.get(d)
            if a and a not in found:
                found.append(a)
    return sorted(found)


def analyze(root: Path, cfg: dict) -> dict:
    return {
        "path": str(root),
        "version": version_of(root),
        "headers": header_arches(root, cfg),
        "simulators": sim_arches(root, cfg),
    }


def candidates() -> list[Path]:
    env = os.environ.get("ASCEND_HOME_PATH")
    seeds: list[Path] = []
    if env:
        seeds.append(Path(env))
    # scan ~/Ascend, /usr/local/Ascend, and ~/Ascend_* (full/new/910) two levels deep
    bases = [Path.home() / "Ascend", Path("/usr/local/Ascend")]
    bases += [p for p in Path.home().iterdir() if p.is_dir() and p.name.startswith("Ascend")]
    for base in bases:
        if not base.exists():
            continue
        for d in base.iterdir():
            if d.is_dir():
                seeds.append(d)
                for g in d.iterdir():
                    if g.is_dir():
                        seeds.append(g)
    seen: set[Path] = set()
    out: list[Path] = []
    for p in seeds:
        r = p.resolve()
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def looks_like_toolkit(root: Path) -> bool:
    # A real CANN toolkit root carries its own version file; nested dirs such
    # as 'x86_64-linux/' or 'toolkit/' (which expose headers/sim but no version)
    # are excluded so they don't show up as duplicates.
    return (
        (root / "compiler" / "version.info").exists()
        or (root / "opp" / "version.info").exists()
        or (root / "version.cfg").exists()
    )


def print_row(info: dict, cfg: dict) -> None:
    note = ""
    for kt in cfg.get("known_toolkits", []):
        if kt.get("version") == info["version"]:
            note = f"  [{', '.join(kt.get('machines', []))}] {kt.get('note', '')}"
            break
    headers = " ".join(info["headers"]) if info["headers"] else "-"
    sims = " ".join(info["simulators"]) if info["simulators"] else "-"
    print(f"{info['path']}\n  version: {info['version']}\n  headers: {headers}\n  simulator: {sims}")
    if note:
        print(f"  {note}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Detect CANN toolkit arch support.")
    ap.add_argument("--home", help="Analyze a single CANN toolkit path.")
    ap.add_argument("--scan", action="store_true", help="Scan ~/Ascend and /usr/local/Ascend.")
    ap.add_argument("--json", action="store_true", help="Emit JSON.")
    args = ap.parse_args(argv)

    cfg = load_config()

    if args.home:
        roots = [Path(args.home).expanduser().resolve()]
    elif args.scan or not os.environ.get("ASCEND_HOME_PATH"):
        roots = candidates()
    else:
        roots = [Path(os.environ["ASCEND_HOME_PATH"]).resolve()]

    infos = [analyze(r, cfg) for r in roots if looks_like_toolkit(r)]
    if not infos:
        print("No CANN toolkits found. Set ASCEND_HOME_PATH or run --scan.", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"tookits": infos}, indent=2))
        return 0

    for info in infos:
        print_row(info, cfg)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())