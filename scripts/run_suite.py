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
import concurrent.futures
import datetime as _dt
import json
import os
import re
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
import capabilities  # noqa: E402
import perf_metrics  # noqa: E402
import targets  # noqa: E402
from _term import fmt_dur  # noqa: E402

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


def _set_flag(cmd: list[str], flag: str, value: str) -> list[str]:
    if flag in cmd:
        i = cmd.index(flag)
        if i + 1 < len(cmd):
            cmd[i + 1] = value
        else:
            cmd.append(value)
    else:
        cmd += [flag, value]
    return cmd


def build_command(suite: dict, arches: dict, repo: Path,
                  testcase: str | None = None, gtest_filter: str | None = None) -> list[str]:
    arch = suite.get("arch") or ""
    arch_info = arches.get(arch) or {}
    subst = {
        "arch": arch,
        "soc": arch_info.get("soc", ""),
        "soc_version": arch_info.get("soc_version", ""),
        "repo": str(repo),
        "testcase": testcase or suite.get("testcase", "all"),
        "filter": gtest_filter or "",
    }
    cmd = [tok.format(**subst) for tok in suite.get("command", [])]

    # Inject a single-testcase / gtest-filter selection per runner convention.
    mode = suite.get("mode") or ""
    runner = suite.get("runner") or ("cpu" if mode == "cpu"
                                     else ("run_st" if mode in ("npu-sim", "npu", "comm") else "generic"))
    if runner == "cpu":
        if testcase:
            cmd += ["--testcase", testcase]
        if gtest_filter:
            cmd += ["--gtest_filter", gtest_filter]
    elif runner == "run_st":
        cmd = _set_flag(cmd, "-t", testcase or "all")
        if gtest_filter:
            cmd = _set_flag(cmd, "-g", gtest_filter)
    # runner == "generic": the command template handles {testcase}/{filter} itself
    return cmd


def _empty_results(name: str, status: str, evidence: list[str]) -> dict:
    return {
        "suite": name,
        "summary": {"passed": 0, "failed": 0, "skipped": 0, "total": 0, "status": status},
        "cases": [],
        "evidence": evidence,
    }


def extract_error(log_text: str) -> str | None:
    """Pull the most likely root-cause line out of a failing run's log."""
    lines = [l.strip() for l in log_text.splitlines() if l.strip()]
    for l in lines:
        if re.search(r"segmentation fault|\bfatal error:", l, re.I):
            return l[:200]
    for l in lines:
        if re.search(r"\berror:|run failed:", l, re.I):
            return l[:200]
    return None


def _error_result(suite: dict, cmd: list[str], message: str) -> dict:
    return {
        "name": suite["name"],
        "mode": suite.get("mode"),
        "status": "ERROR",
        "exit_code": None,
        "timed_out": False,
        "duration_s": None,
        "command": cmd,
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
            run_dir: Path, quiet: bool, tui: bool,
            testcase: str | None = None, gtest_filter: str | None = None) -> dict:
    mode = suite.get("mode") or ""
    cmd = build_command(suite, arches, repo, testcase, gtest_filter)
    if mode in NEEDS_ASCEND and not os.environ.get("ASCEND_HOME_PATH"):
        return _error_result(suite, cmd, "ASCEND_HOME_PATH not set — source ./env.sh (or export it) before running npu/costmodel/comm suites.")

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

    log_text = log_file.read_text(encoding="utf-8", errors="replace")
    results = parse_gtest.parse_text(log_text, suite["name"])
    status = "TIMEOUT" if timed_out else ("PASS" if exit_code == 0 else "FAIL")
    error = None
    if status == "FAIL":
        error = extract_error(log_text)
    elif status == "TIMEOUT":
        error = f"TIMEOUT after {timeout_s}s"

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
        "perf_copy": suite.get("perf_copy"),
        "error": error,
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
    for s in record["suites"]:
        if s.get("error"):
            print(f"  ⚠  {s['name']}: {s['error']}")


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
            "error": s.get("error"),
        })
    return {"run_id": record["run_id"], "target": record["target"], "suites": suites}


def _suite_rows(target_cfg: dict, arches: dict):
    rows = []
    for s in target_cfg.get("suites", []):
        runnable, reason = capabilities.suite_reason(s, arches)
        rows.append({
            "name": s.get("name", ""),
            "mode": s.get("mode", "-"),
            "arch": s.get("arch") or "-",
            "enabled": bool(s.get("enabled")),
            "runnable": runnable,
            "reason": reason,
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
    suites = _suite_rows(targets[target], arches)
    archs = _arch_rows(arches)

    if fmt == "markdown":
        print(f"# Suites — {target}\n")
        print("| suite | mode | arch | status | milestone | description |")
        print("|---|---|---|---|---|---|")
        for s in suites:
            st = "✓" if (s["enabled"] and s["runnable"]) else ("!" if s["enabled"] else "—")
            desc = s["description"] if s["runnable"] else f"{s['description']} ({s['reason']})"
            print(f"| {s['name']} | {s['mode']} | {s['arch']} | {st} | {s['milestone']} | {desc} |")
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
            f"<td>{html.escape(s['arch'])}</td>"
            f"<td>{'✓' if (s['enabled'] and s['runnable']) else ('!' if s['enabled'] else '—')}</td>"
            f"<td>{html.escape(s['milestone'])}</td>"
            f"<td>{html.escape(s['description'] if s['runnable'] else s['description'] + ' (' + s['reason'] + ')')}</td></tr>"
            for s in suites)
        arch_html = "".join(
            f"<tr><td>{html.escape(a['name'])}</td><td>{html.escape(a['soc'])}</td>"
            f"<td>{html.escape(a['march'])}</td><td>{html.escape(a['chip'])}</td></tr>"
            for a in archs)
        print(f"""<!doctype html><html><head><meta charset=\"utf-8\"><title>Suites</title>
<style>body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:2rem}}table{{border-collapse:collapse;margin:1rem 0}}th,td{{border:1px solid #ddd;padding:.4rem .6rem;text-align:left}}th{{background:#f5f5f5}}</style>
</head><body><h1>Run catalog — {html.escape(target)}</h1>
<h2>Suites</h2><table><thead><tr><th>suite</th><th>mode</th><th>arch</th><th>status</th><th>milestone</th><th>description</th></tr></thead><tbody>{suites_html}</tbody></table>
<h2>Arches</h2><table><thead><tr><th>arch</th><th>soc</th><th>march</th><th>chip</th></tr></thead><tbody>{arch_html}</tbody></table>
</body></html>""")
        return 0

    print(f"\nSuites for '{target}' — ✓ enabled+runnable, ! enabled-but-missing, — disabled:")
    for s in suites:
        if s["enabled"] and s["runnable"]:
            mark = "✓"
        elif s["enabled"]:
            mark = "!"
        else:
            mark = " "
        note = "" if (s["runnable"] or not s["enabled"]) else f"  ← {s['reason']}"
        print(f"  [{mark}] {s['name']:<16} mode={s['mode']:<9} arch={s['arch']:<6} "
              f"({s['milestone']}) {s['description']}{note}")
    print("\nArches:")
    for a in archs:
        print(f"  {a['name']:<8} soc={a['soc']:<18} march={a['march']:<16} {a['chip']}")
    return 0


def _print_next_steps(record: dict, failed: bool, as_json: bool) -> None:
    n_failed = sum(1 for s in record["suites"] if s.get("status") != "PASS")
    if failed:
        lines = [
            f"⚠ {n_failed} suite(s) failed.",
            "next: ./harness report --open   (see the failure)   → triage → ./harness teach \"…\"",
        ]
    else:
        lines = [
            "✓ all passed.",
            "next: ./harness report --open   or   ./harness review   (diff vs baseline)",
        ]
    if as_json:
        for l in lines:
            print(l, file=sys.stderr)
    else:
        print()
        for l in lines:
            print("  " + l)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run a declared regression suite and record a normalized run.")
    ap.add_argument("--target", default=None, help="Target key in config/suites.json (default: config default_target).")
    ap.add_argument("--suite", default=None, help="Suite name, or omit with --all-suites.")
    ap.add_argument("--all-suites", action="store_true", help="Run all enabled suites for the target.")
    ap.add_argument("--testcase", default=None, help="Run a single testcase inside the selected suite (e.g. tpartargmax).")
    ap.add_argument("--filter", default=None, help="gtest filter applied to the suite (e.g. 'TADDTest.case_*').")
    ap.add_argument("--quiet", "-q", action="store_true", help="Suppress per-suite output; print only the summary.")
    ap.add_argument("--tui", action="store_true", help="Live per-suite spinner + pass/fail line (no raw output).")
    ap.add_argument("--parallel", action="store_true", help="Run independent suites concurrently (implies per-suite quiet).")
    ap.add_argument("--json", action="store_true", help="Print the summary as JSON instead of a table.")
    ap.add_argument("--dry-run", action="store_true", help="Print what WOULD run and exit (no run.json).")
    ap.add_argument("--list", action="store_true", help="List suites + arches and exit.")
    ap.add_argument("--format", choices=["text", "markdown", "html"], default="text",
                    help="Output format for --list (default text).")
    ap.add_argument("--run-id", default=None, help="Run id; defaults to <ts>-<target>.")
    ap.add_argument("--config", default=str(HARNESS / "config" / "suites.json"))
    ap.add_argument("--arches", default=str(HARNESS / "config" / "arches.json"))
    args = ap.parse_args(argv)

    cfg = load_json(Path(args.config))
    if args.target is None:
        args.target = targets.default_target(cfg)
    if args.target not in cfg.get("targets", {}):
        usage_error(f"unknown target '{args.target}'. Known: {targets.list_targets(cfg)}")

    if args.list:
        return list_all(Path(args.config), Path(args.arches), args.target, args.format)

    arches = load_json(Path(args.arches))
    target_cfg = cfg["targets"][args.target]

    repo = resolve_repo(target_cfg)
    if not repo.exists():
        usage_error(f"target repo not found: {repo} (set {target_cfg.get('repo_env', 'PTO_ISA_REPO')} or source ./env.sh — see ./harness diagnose)")

    if args.run_id:
        sane = re.sub(r"[^A-Za-z0-9._-]+", "-", args.run_id).strip(".-")
        if sane != args.run_id:
            print(f"warning: sanitized run-id '{args.run_id}' -> '{sane}'", file=sys.stderr)
        run_id = sane or f"{_dt.datetime.now():%Y%m%d-%H%M%S}-{args.target}"
    else:
        run_id = f"{_dt.datetime.now():%Y%m%d-%H%M%S}-{args.target}"

    if not args.all_suites and args.suite is None:
        enabled = [s["name"] for s in target_cfg.get("suites", []) if s.get("enabled")]
        usage_error(
            "specify --suite <name> or --all-suites.\n"
            f"Enabled suites for '{args.target}': {enabled or 'none'}\n"
            "see ./harness list (what can run) or ./harness diagnose (what's missing)"
        )

    if args.all_suites and (args.testcase or args.filter):
        usage_error("--testcase / --filter can only be used with a single --suite, not --all-suites.")

    suites = select_suites(target_cfg, None if args.all_suites else args.suite)
    if not suites:
        usage_error("no enabled suites matched; check config/suites.json")

    # auto-detect availability: for --all-suites, skip suites whose prerequisites
    # are missing in this environment (explicit --suite still force-runs them).
    if args.all_suites:
        runnable: list[dict] = []
        for s in suites:
            ok, reason = capabilities.suite_reason(s, arches)
            if ok:
                runnable.append(s)
            else:
                print(f"  skip {s['name']}: {reason}")
        if not runnable and not args.dry_run:
            usage_error("none of the enabled suites are runnable in this environment; see ./harness list / ./harness diagnose.")
        suites = runnable

    if args.dry_run:
        print(f"\ndry-run: would run {len(suites)} suite(s) for '{args.target}':")
        if not suites:
            print("  (none — every enabled suite was skipped above)")
        for s in suites:
            tmo = s.get("timeout_s") or 0
            upto = f"  (up to {tmo // 60}m)" if tmo else ""
            print(f"  - {s['name']:<16} mode={s.get('mode', ''):<9}{upto}")
        print("no run.json written (dry-run).")
        return 0

    run_dir = HARNESS / "reports" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

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

    run_quiet = args.quiet or args.json
    tui = args.tui and not args.json and sys.stdout.isatty()
    parallel = args.parallel and len(suites) > 1 and not tui and not args.json
    if parallel:
        print(f"  running {len(suites)} suites in parallel (--parallel)", file=sys.stderr)
        results: dict[int, dict] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(suites)) as ex:
            futs = {
                ex.submit(run_one, repo, suite, arches, target_cfg, run_dir, True, False,
                          args.testcase, args.filter): i
                for i, suite in enumerate(suites)
            }
            for fut in concurrent.futures.as_completed(futs):
                results[futs[fut]] = fut.result()
        record["suites"] = [results[i] for i in sorted(results)]
    else:
        for suite in suites:
            record["suites"].append(
                run_one(repo, suite, arches, target_cfg, run_dir, run_quiet, tui, args.testcase, args.filter)
            )

    # Attach per-suite analytics: per-case timing + optional CAModel metrics.
    for s in record["suites"]:
        cases = (s.get("results") or {}).get("cases", [])
        s["timing"] = perf_metrics.duration_stats(cases)
        perf_metrics.copy_perf(repo, run_dir, s.get("name", ""),
                               s.get("perf_copy"), args.testcase or s.get("testcase"))
        perf = perf_metrics.collect_perf(run_dir, s.get("name", ""))
        if perf:
            s["perf"] = perf

    run_json = run_dir / "run.json"
    run_json.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(summary_object(record), indent=2))
        print(f"Wrote {run_json}", file=sys.stderr)
    else:
        print_summary(record)
        print(f"\nWrote {run_json}")

    failed = any(s.get("status") != "PASS" for s in record["suites"])
    _print_next_steps(record, failed, args.json)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())