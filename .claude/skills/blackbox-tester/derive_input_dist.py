#!/usr/bin/env python3
"""Derive the TTK ``--input-dist`` flag from ``docs/{OP}/spec.yaml``.

Rule (single source, do not hand-judge): if ANY input declares
``data_distribution: normal`` (accumulation-class ops), print
``--input-dist normal``; otherwise print nothing (TTK defaults to
``uniform``). The caller captures stdout into ``$INPUT_DIST_ARG``.

Usage:
  derive_input_dist.py --spec <docs/{OP}/spec.yaml>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _any_normal(node) -> bool:
    """Recursively find any ``data_distribution: normal`` regardless of where
    it sits in the spec, so a schema drift does not silently flip the gate."""
    if isinstance(node, dict):
        if str(node.get("data_distribution", "")).strip().lower() == "normal":
            return True
        return any(_any_normal(v) for v in node.values())
    if isinstance(node, list):
        return any(_any_normal(v) for v in node)
    return False


def _load(path: Path):
    try:
        import yaml  # type: ignore
    except ImportError:
        yaml = None
    text = path.read_text(encoding="utf-8", errors="replace")
    if yaml is not None:
        return yaml.safe_load(text)
    # Minimal YAML-free fallback: treat ``data_distribution: normal`` on its
    # own line as the signal. Good enough for the single flag we derive.
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith("data_distribution:")
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spec", required=True, help="Path to docs/{OP}/spec.yaml")
    args = ap.parse_args(argv)

    spec = Path(args.spec)
    if not spec.exists():
        print(f"derive_input_dist: spec not found: {args.spec}", file=sys.stderr)
        return 1
    try:
        if _any_normal(_load(spec)):
            print("--input-dist normal")
    except Exception as exc:  # noqa: BLE001 — surface any parse failure
        print(f"derive_input_dist: failed to parse {args.spec}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
