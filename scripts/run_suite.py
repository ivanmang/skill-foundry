#!/usr/bin/env python3
"""Run a declared regression suite and produce a normalized run record.

Usage:
  python3 scripts/run_suite.py --suite cpu-st                 # default target: pto-isa
  python3 scripts/run_suite.py --all-suites
  python3 scripts/run_suite.py --quiet --all-suites           # summary only
  python3 scripts/run_suite.py --list                        # list suites + arches
  python3 scripts/run_suite.py --target demo --all-suites     # demo target

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
import threading
import time
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import parse_gtest  # noqa: E402

# Modes that need a CANN toolkit (ASCEND_HOME_PATH) on the runner.
NEEDS_ASCEND = {"npu-sim", "npu", "costmodel", "comm"}

SPINNER = "|/-\\"


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def git_ref(path: Path) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=30)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def git_dirty(path: Path) -> bool | None:
    try:
        out = subprocess.run(["git", "-C", str(path), "status", "--porcelain"],
                             capture_output=True, text=True, timeout=30)
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


def usage_error(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(2)


def fmt_dur(sec: float | None) -> str:
    if sec is None:
        return "-"
    if sec < 1:
        return f"{sec * 1000:.0f}ms"
    return f"{sec:.2f}s"


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


def _empty_results(name: str, status: str, evidence: list[str]) -> dict:
    return {
        "suite": name,
        "summary": {"passed": 0, "failed": 0, "skipped": 0, "total": 0, "status": status},
        "cases": [],
        "evidence": evidence,
    }


def _error_result(suite: dict, message: str) -> dict:
    return {
        "name": suite["name"],
        "mode": suite.get("mode"),
        "status": "ERROR",
        "exit_code": None,
        "timed_out": False,
        "duration_s": None,
        "command": suite.get("command", []),
        "log_file": None,
        "description": suite.get("description", ""),
        "error": message,
        "results": _empty_results(suite["name"], "ERROR", [message]),
    }


def _popen_run(script: str, repo: Path, log_file: Path, timeout_s: int,
               on_line=None) -> tuple[int | None, bool, float]:
    start = time.perf_counter()
    exit_code: int | None = None
    timed_out = False
    with log_file.open("w", encoding="utf-8") as lf:
        proc = subprocess.Popen(
            ["bash", "-c", script], cwd=str(repo),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                if on_line:
                    on_line(line)
                lf.write(line)
            proc.wait(timeout=timeout_s)
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            proc.wait()
            exit_code = proc.returncode
            lf.write(f"\n[harness] TIMEOUT after {timeout_s}s\n")
    return exit_code, timed_out, round(time.perf_counter() - start, 3)


def run_one(repo: Path, suite: dict, arches: dict, target_cfg: dict,
            run_dir: Path, quiet: bool, tui: bool) -> dict:
    mode = suite.get("mode") or ""
    if mode in NEEDS_ASCEND and not os.environ.get("ASCEND_HOME_PATH"):
        return _error_result(suite, "ASCEND_HOME_PATH not set — source ./env.sh (or export it) before running npu/costmodel/comm suites.")

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

    if tui:
        start = time.perf_counter()
        stop = threading.Event()

        def spin() -> None:
            i = 0
            while not stop.is_set():
                elapsed = time.perf_counter() - start
                sys.stdout.write(f"\r  {SPINNER[i % len(SPINNER)]} {suite['name']} … {elapsed:.0f}s")
                sys.stdout.flush()
                i += 1
                stop.wait(0.1)

        t = threading.Thread(target=spin, daemon=True)
        t.start()
        exit_code, timed_out, duration_s = _popen_run(script, repo, log_file, timeout_s)
        stop.set()
        t.join(timeout=0.3)
        sys.stdout.write("\r" + " " * 60 + "\r")
        sys.stdout.flush()
        status = "TIMEOUT" if timed_out else ("PASS" if exit_code == 0 else "FAIL")
        mark = "⏱" if timed_out else ("✓" if status == "PASS" else "✗")
        print(f"{mark} {suite['name']} — {status} ({fmt_dur(duration_s)})")
    else:
        if not quiet:
            print(f"\n=== {suite['name']} ===")
        on_line = None if quiet else sys.stdout.write
        exit_code, timed_out, duration_s = _popen_run(script, repo, log_file, timeout_s, on_line)

    results = parse_gtest.parse_text(log_file.read_text(encoding="utf-8", errors="replace"), suite["name"])
    status = "TIMEOUT" if timed_out else ("PASS" if exit_code == 0 else "FAIL")

    return {
        "name": suite["name"],
        "mode": mode,
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
    usage_error(f"unknown suite '{suite_arg}'. Known: {[s['name'] for s in suites]}")
    raise AssertionError("unreachable")


def print_summary(record: dict) -> None:
    headers = ["suite", "status", "pass", "fail", "skip", "total", "duration"]
    rows = []
    for s in record["suites"]:
        sm = (s.get("results") or {}).get("summary") or {}
        rows.append([
            s["name"], s.get("status", "?"),
            str(sm.get("passed", 0)), str(sm.get("failed", 0)),
            str(sm.get("skipped", 0)), str(sm.get("total", 0)),
            fmt_dur(s.get("duration_s")),
        ])
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]

    def line(cols):
        return "| " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(cols)) + " |"

    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    print("\n" + sep)
    print(line(headers))
    print(sep)
    for r in rows:
        print(line(r))
    print(sep)


def summary_object(record: dict) -> dict:
    suites = []
    for s in record["suites"]:
        sm = (s.get("results") or {}).get("summary") or {}
        suites.append({
            "name": s["name"],
            "status": s.get("status"),
            "passed": sm.get("passed", 0),
            "failed": sm.get("failed", 0),
            "skipped": sm.get("skipped", 0),
            "total": sm.get("total", 0),
            "duration_s": s.get("duration_s"),
        })
    return {"run_id": record["run_id"], "target": record["target"], "suites": suites}


def _suite_rows(target_cfg: dict):
    rows = []
    for s in target_cfg.get("suites", []):
        rows.append({
            "name": s.get("name", ""),
            "mode": s.get("mode", "-"),
            "arch": s.get("arch") or "-",
            "enabled": bool(s.get("enabled")),
            "milestone": s.get("milestone", ""),
            "description": s.get("description", ""),
        })
    return rows


def _arch_rows(arches: dict):
    rows = []
    for name, a in arches.items():
        rows.append({
            "name": name,
            "soc": a.get("soc", "-"),
            "march": a.get("march") or "-",
            "chip": a.get("chip", ""),
        })
    return rows


def list_all(cfg_path: Path, arches_path: Path, target: str, fmt: str) -> int:
    cfg = load_json(cfg_path)
    arches = load_json(arches_path)
    targets = cfg.get("targets", {})
    if target not in targets:
        usage_error(f"unknown target '{target}'. Known: {list(targets)}")
    suites = _suite_rows(targets[target])
    archs = _arch_rows(arches)

    if fmt == "markdown":
        print(f"# Suites — {target}\n")
        print("| suite | mode | arch | enabled | milestone | description |")
        print("|---|---|---|---|---|---|")
        for s in suites:
            print(f"| {s['name']} | {s['mode']} | {s['arch']} | {'✓' if s['enabled'] else ''} | {s['milestone']} | {s['description']} |")
        print("\n# Arches\n")
        print("| arch | soc | march | chip |")
        print("|---|---|---|---|")
        for a in archs:
            print(f"| {a['name']} | {a['soc']} | {a['march']} | {a['chip']} |")
        return 0

    if fmt == "html":
        import html
        suites_html = "".join(
            f"<tr><td>{html.escape(s['name'])}</td><td>{html.escape(s['mode'])}</td>"
            f"<td>{html.escape(s['arch'])}</td><td>{'✓' if s['enabled'] else ''}</td>"
            f"<td>{html.escape(s['milestone'])}</td><td>{html.escape(s['description'])}</td></tr>"
            for s in suites)
        arch_html = "".join(
            f"<tr><td>{html.escape(a['name'])}</td><td>{html.escape(a['soc'])}</td>"
            f"<td>{html.escape(a['march'])}</td><td>{html.escape(a['chip'])}</td></tr>"
            for a in archs)
        print(f"""<!doctype html><html><head><meta charset=\"utf-8\"><title>Suites</title>
<style>body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:2rem}}table{{border-collapse:collapse;margin:1rem 0}}th,td{{border:1px solid #ddd;padding:.4rem .6rem;text-align:left}}th{{background:#f5f5f5}}</style>
</head><body><h1>Run catalog — {html.escape(target)}</h1>
<h2>Suites</h2><table><thead><tr><th>suite</th><th>mode</th><th>arch</th><th>enabled</th><th>milestone</th><th>description</th></tr></thead><tbody>{suites_html}</tbody></table>
<h2>Arches</h2><table><thead><tr><th>arch</th><th>soc</th><th>march</th><th>chip</th></tr></thead><tbody>{arch_html}</tbody></table>
</body></html>""")
        return 0

    print(f"\nSuites for '{target}':")
    for s in suites:
        mark = "✓" if s["enabled"] else " "
        print(f"  [{mark}] {s['name']:<16} mode={s['mode']:<9} arch={s['arch']:<6} "
              f"({s['milestone']}) {s['description']}")
    print("\nArches:")
    for a in archs:
        print(f"  {a['name']:<8} soc={a['soc']:<18} march={a['march']:<16} {a['chip']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run a declared regression suite and record a normalized run.")
    ap.add_argument("--target", default="pto-isa", help="Target key in config/suites.json (default pto-isa).")
    ap.add_argument("--suite", default=None, help="Suite name, or omit with --all-suites.")
    ap.add_argument("--all-suites", action="store_true", help="Run all enabled suites for the target.")
    ap.add_argument("--quiet", "-q", action="store_true", help="Suppress per-suite output; print only the summary.")
    ap.add_argument("--tui", action="store_true", help="Live per-suite spinner + pass/fail line (no raw output).")
    ap.add_argument("--json", action="store_true", help="Print the summary as JSON instead of a table.")
    ap.add_argument("--list", action="store_true", help="List suites + arches and exit.")
    ap.add_argument("--format", choices=["text", "markdown", "html"], default="text",
                    help="Output format for --list (default text).")
    ap.add_argument("--run-id", default=None, help="Run id; defaults to <ts>-<target>.")
    ap.add_argument("--config", default=str(HARNESS / "config" / "suites.json"))
    ap.add_argument("--arches", default=str(HARNESS / "config" / "arches.json"))
    args = ap.parse_args(argv)

    if args.list:
        return list_all(Path(args.config), Path(args.arches), args.target, args.format)

    cfg = load_json(Path(args.config))
    arches = load_json(Path(args.arches))
    targets = cfg.get("targets", {})
    if args.target not in targets:
        usage_error(f"unknown target '{args.target}'. Known: {list(targets)}")
    target_cfg = targets[args.target]

    repo = resolve_repo(target_cfg)
    if not repo.exists():
        usage_error(f"target repo not found: {repo} (set {target_cfg.get('repo_env', 'PTO_ISA_REPO')} or source ./env.sh)")

    run_id = args.run_id or f"{_dt.datetime.now():%Y%m%d-%H%M%S}-{args.target}"
    run_dir = HARNESS / "reports" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    if not args.all_suites and args.suite is None:
        enabled = [s["name"] for s in target_cfg.get("suites", []) if s.get("enabled")]
        usage_error(
            "specify --suite <name> or --all-suites.\n"
            f"Enabled suites for '{args.target}': {enabled or 'none'}"
        )

    suites = select_suites(target_cfg, None if args.all_suites else args.suite)
    if not suites:
        usage_error("no enabled suites matched; check config/suites.json")

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

    tui = args.tui and sys.stdout.isatty()
    for suite in suites:
        record["suites"].append(run_one(repo, suite, arches, target_cfg, run_dir, args.quiet, tui))

    run_json = run_dir / "run.json"
    run_json.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(summary_object(record), indent=2))
    else:
        print_summary(record)
    print(f"\nWrote {run_json}")

    failed = any(s.get("status") != "PASS" for s in record["suites"])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())