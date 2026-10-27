#!/usr/bin/env python3
"""Run a declared regression suite and produce a normalized run record.

Usage:
  python3 scripts/run_suite.py --target pto-isa --suite cpu-st
  python3 scripts/run_suite.py --target pto-isa --all-suites
  python3 scripts/run_suite.py --target pto-isa --suite npu-sim-a5 --run-id smoke

Writes reports/<run-id>/run.json plus one raw log per suite, and normalizes
each log with parse_gtest into the suite's "results" field.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shlex
import socket
import subprocess
import sys
import time
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import parse_gtest  # noqa: E402


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def git_ref(path: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=30,
        )
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def git_dirty(path: Path) -> bool | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(path), "status", "--porcelain"],
            capture_output=True, text=True, timeout=30,
        )
        return bool(out.stdout.strip()) if out.returncode == 0 else None
    except Exception:
        return None


def resolve_repo(target_cfg: dict) -> Path:
    env_name = target_cfg.get("repo_env") or "PTO_ISA_REPO"
    raw = os.environ.get(env_name) or target_cfg.get("repo_default") or "~/pto-isa"
    return Path(raw).expanduser().resolve()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_command(suite: dict, arches: dict, repo: Path) -> list[str]:
    arch = suite.get("arch") or ""
    arch_info = arches.get(arch) or {}
    subst = {
        "arch": arch,
        "soc": arch_info.get("soc", ""),
        "soc_version": arch_info.get("soc_version", ""),
        "repo": str(repo),
        "testcase": suite.get("testcase", "all"),
    }
    return [tok.format(**subst) for tok in suite.get("command", [])]


def run_one(repo: Path, suite: dict, arches: dict, target_cfg: dict, run_dir: Path) -> dict:
    cmd = build_command(suite, arches, repo)
    env_setup = target_cfg.get("env_setup", "") or ""
    env = target_cfg.get("env", {}) or {}

    script = "set -o pipefail\n"
    if env_setup:
        script += env_setup + "\n"
    for k, v in env.items():
        script += f"export {k}={shlex.quote(v)}\n"
    script += "exec " + shlex.join(cmd) + "\n"

    log_file = run_dir / f"{suite['name']}.log"
    timeout_s = int(suite.get("timeout_s", 7200))

    start = time.perf_counter()
    exit_code = None
    timed_out = False
    with log_file.open("w", encoding="utf-8") as lf:
        proc = subprocess.Popen(
            ["bash", "-c", script],
            cwd=str(repo),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                sys.stdout.write(line)
                lf.write(line)
            proc.wait(timeout=timeout_s)
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            proc.wait()
            exit_code = proc.returncode
            lf.write(f"\n[harness] TIMEOUT after {timeout_s}s\n")
    duration_s = round(time.perf_counter() - start, 3)

    log_text = log_file.read_text(encoding="utf-8", errors="replace")
    results = parse_gtest.parse_text(log_text, suite["name"])

    status = "TIMEOUT" if timed_out else ("PASS" if exit_code == 0 else "FAIL")

    return {
        "name": suite["name"],
        "mode": suite.get("mode"),
        "status": status,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "duration_s": duration_s,
        "command": cmd,
        "log_file": str(log_file.relative_to(HARNESS)),
        "description": suite.get("description", ""),
        "results": results,
    }


def select_suites(target_cfg: dict, suite_arg: str | None) -> list[dict]:
    suites = target_cfg.get("suites", [])
    if suite_arg in (None, "all"):
        return [s for s in suites if s.get("enabled", False)]
    for s in suites:
        if s["name"] == suite_arg:
            return [s]
    raise SystemExit(f"unknown suite '{suite_arg}'. Known: {[s['name'] for s in suites]}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run a declared regression suite and record a normalized run.")
    ap.add_argument("--target", required=True, help="Target key in config/suites.json.")
    ap.add_argument("--suite", default=None, help="Suite name, or omit with --all-suites.")
    ap.add_argument("--all-suites", action="store_true", help="Run all enabled suites for the target.")
    ap.add_argument("--run-id", default=None, help="Run id; defaults to <ts>-<target>.")
    ap.add_argument("--config", default=str(HARNESS / "config" / "suites.json"))
    ap.add_argument("--arches", default=str(HARNESS / "config" / "arches.json"))
    args = ap.parse_args(argv)

    cfg = load_json(Path(args.config))
    arches = load_json(Path(args.arches))
    targets = cfg.get("targets", {})
    if args.target not in targets:
        raise SystemExit(f"unknown target '{args.target}'. Known: {list(targets)}")
    target_cfg = targets[args.target]

    repo = resolve_repo(target_cfg)
    if not repo.exists():
        raise SystemExit(f"target repo not found: {repo} (set {target_cfg.get('repo_env', 'PTO_ISA_REPO')})")

    run_id = args.run_id or f"{_dt.datetime.now():%Y%m%d-%H%M%S}-{args.target}"
    run_dir = HARNESS / "reports" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    suites = select_suites(target_cfg, None if args.all_suites else args.suite)
    if not suites:
        raise SystemExit("no enabled suites matched; check config/suites.json")

    record = {
        "run_id": run_id,
        "generated_at": now_iso(),
        "generated": True,
        "harness_commit": git_ref(HARNESS),
        "target": args.target,
        "target_repo": str(repo),
        "target_commit": git_ref(repo),
        "target_dirty": git_dirty(repo),
        "host": socket.gethostname(),
        "env_snapshot": {
            "ASCEND_HOME_PATH": os.environ.get("ASCEND_HOME_PATH", ""),
            "PATH": os.environ.get("PATH", ""),
        },
        "suites": [],
    }

    for suite in suites:
        print(f"\n=== {args.target}/{suite['name']} ===")
        record["suites"].append(run_one(repo, suite, arches, target_cfg, run_dir))

    run_json = run_dir / "run.json"
    run_json.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {run_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())