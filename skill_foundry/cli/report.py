#!/usr/bin/env python3
"""Turn run record(s) into Markdown + self-contained HTML reports.

Usage:
  python3 -m skill_foundry.cli.report --run reports/<id>/run.json --out reports/<id>/report
  python3 -m skill_foundry.cli.report --run a.json --run b.json --out combined/report

Optionally annotate failures against a known-failures file (the triage corpus
kept by the harness). Pass --known to mark matched failures as known:

  python3 -m skill_foundry.cli.report --run reports/<id>/run.json \
      --known .claude/skills/pto-isa/references/known-failures.md \
      --out reports/<id>/report
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

from skill_foundry.lib import runs as _runs  # noqa: E402
from skill_foundry.lib import browser as _browser  # noqa: E402
from skill_foundry.lib.term import fmt_dur  # noqa: E402



def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_known_signatures(path: str | None) -> list[str]:
    """Extract '### <signature>' headers from a known-failures markdown file."""
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    sigs: list[str] = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if s.startswith("###"):
            sigs.append(s[3:].strip())
    return sigs


def suite_rows(record: dict) -> list[list[str]]:
    rows = []
    for s in record.get("suites", []):
        r = s.get("results") or {}
        sm = r.get("summary") or {}
        perf = s.get("perf") or {}
        vf = perf.get("vf_real")
        cycles = "-" if vf is None else str(vf)
        rows.append([
            s.get("name", "?"),
            str(sm.get("passed", 0)),
            str(sm.get("failed", 0)),
            str(sm.get("skipped", 0)),
            str(sm.get("total", 0)),
            s.get("status", "UNKNOWN"),
            fmt_dur(s.get("duration_s")),
            cycles,
        ])
    return rows


def timing_rows(record: dict) -> list[list[str]]:
    """Per-suite timing: suite duration always, per-case stats when captured."""
    rows = []
    for s in record.get("suites", []):
        t = s.get("timing") or {}

        def f(v):
            return "-" if v is None else fmt_dur(v)

        rows.append([
            s.get("name", "?"),
            str(t.get("cases", 0)),
            fmt_dur(s.get("duration_s")),
            f(t.get("min")), f(t.get("p50")), f(t.get("p99")), f(t.get("max")),
        ])
    return rows


def command_rows(record: dict) -> list[list[str]]:
    """Per-suite command / exit code / raw log path."""
    rows = []
    for s in record.get("suites", []):
        exit_code = s.get("exit_code")
        rows.append([
            s.get("name", "?"),
            str(exit_code) if exit_code is not None else "-",
            s.get("log_file", ""),
            " ".join(str(x) for x in s.get("command", [])),
        ])
    return rows


def case_rows(record: dict) -> list[dict]:
    """Per-case rows: suite, case name, status, duration_s (None = not measured)."""
    rows = []
    for s in record.get("suites", []):
        r = s.get("results") or {}
        for c in r.get("cases", []):
            dur = c.get("duration_s")
            if dur == 0.0:
                dur = None  # 0.0 means the runner didn't measure per-case timing
            rows.append({
                "suite": s.get("name", "?"),
                "name": c.get("name", "?"),
                "status": c.get("status", "?"),
                "duration_s": dur,
            })
    return rows


def perf_rows(record: dict) -> list[list[str]]:
    """Per-suite CAModel metrics (vmi-dashboard schema), only suites that have them."""
    rows = []
    for s in record.get("suites", []):
        p = s.get("perf")
        if not p:
            continue

        def g(k):
            v = p.get(k)
            return "-" if v is None else (f"{v:.3f}" if isinstance(v, float) else str(v))

        rows.append([
            s.get("name", "?"),
            str(p.get("ex", 0)), str(p.get("su", 0)), str(p.get("ld", 0)),
            str(p.get("st", 0)), str(p.get("pred", 0)), str(p.get("scalar", 0)),
            str(p.get("dma", 0)), str(p.get("dual", 0)), str(p.get("stalls", 0)),
            str(p.get("max_stall", 0)), g("ipc"), g("ex_ipc"), str(p.get("vf_real", "-")),
        ])
    return rows


def _matches(sig: str, name: str) -> bool:
    """True if a known-failure signature is about this case name."""
    s, n = sig.lower(), name.lower()
    if s in n:
        return True
    for tok in s.split():
        tok = tok.strip("(),:;[]\"'")
        if len(tok) >= 4 and tok in n:
            return True
    return False


def failures(record: dict, known_sigs: list[str]) -> list[dict]:
    out = []
    for s in record.get("suites", []):
        r = s.get("results") or {}
        for c in r.get("cases", []):
            if c.get("status") == "FAIL":
                name = c.get("name", "")
                hit = next((sig for sig in known_sigs if _matches(sig, name)), None)
                out.append({"suite": s.get("name"), "case": name, "known": hit})
    return out


def _failures_md(fl: list[dict]) -> list[str]:
    lines = ["", "### Failures", ""]
    for f in fl:
        if f["known"]:
            lines.append(f"- `{f['suite']}/{f['case']}` — **known**: {f['known']}")
        else:
            lines.append(f"- `{f['suite']}/{f['case']}`")
    return lines


def render_md(records: list[dict], known_sigs: list[str]) -> str:
    lines: list[str] = ["# Regression Report", ""]
    for rec in records:
        env = rec.get("env_snapshot") or {}
        ascend = env.get("ASCEND_HOME_PATH") or "—"
        lines += [
            f"## Run: {rec.get('run_id')}",
            "",
            f"- target: `{rec.get('target')}`  repo: `{rec.get('target_repo')}`",
            f"- target commit: `{rec.get('target_commit')}`  dirty: {rec.get('target_dirty')}",
            f"- host: `{rec.get('host')}`  ASCEND: `{ascend}`  generated: {rec.get('generated_at')}",
            "",
            "| suite | passed | failed | skipped | total | status | duration | cycles |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for row in suite_rows(rec):
            lines.append("| " + " | ".join(row) + " |")

        cases = case_rows(rec)
        if cases:
            lines += ["", "### Cases", "",
                      "| suite | case | status | duration |",
                      "|---|---|---|---|"]
            for c in cases:
                dur = fmt_dur(c["duration_s"]) if c["duration_s"] is not None else "-"
                lines.append(f"| {c['suite']} | {c['name']} | {c['status']} | {dur} |")

        fl = failures(rec, known_sigs)
        if fl:
            lines += _failures_md(fl)

        trows = timing_rows(rec)
        lines += ["", "### Timing", "",
                  "| suite | cases | duration | min | p50 | p99 | max |",
                  "|---|---|---|---|---|---|---|"]
        for r in trows:
            lines.append("| " + " | ".join(r) + " |")

        prows = perf_rows(rec)
        if prows:
            lines += ["", "### Performance (CA metrics)", "",
                      "| suite | EX | SU | LD | ST | pred | scalar | dma | dual | stalls | max_stall | IPC | EX-IPC | vf_real |",
                      "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
            for r in prows:
                lines.append("| " + " | ".join(r) + " |")

        crows = command_rows(rec)
        lines += ["", "### Commands & logs", "",
                  "| suite | exit | log | command |",
                  "|---|---|---|---|"]
        for r in crows:
            name, exit_code, logpath, cmd = r
            logname = Path(logpath).name if logpath else ""
            logcell = f"[{logpath}]({logname})" if logpath else "-"
            lines.append(f"| {name} | {exit_code} | {logcell} | {cmd} |")

        lines += ["", "---", ""]
    return "\n".join(lines)


def render_html(records: list[dict], known_sigs: list[str]) -> str:
    rows_html = []
    for rec in records:
        env = rec.get("env_snapshot") or {}
        ascend = env.get("ASCEND_HOME_PATH") or "—"
        rows_html.append(
            f'<h2>Run: {html.escape(rec.get("run_id", ""))}</h2>'
            f'<p class="meta">target <code>{html.escape(rec.get("target", ""))}</code> · '
            f'commit <code>{html.escape(rec.get("target_commit", "") or "")}</code> · '
            f'host <code>{html.escape(rec.get("host", ""))}</code> · '
            f'ASCEND <code>{html.escape(ascend)}</code></p>'
        )
        trs = []
        for row in suite_rows(rec):
            status = row[5]
            cls = "ok" if status == "PASS" else ("bad" if status in ("FAIL", "TIMEOUT", "ERROR") else "")
            tds = "".join(
                f'<td class="{cls}">{html.escape(c)}</td>' if i == 5 else f"<td>{html.escape(c)}</td>"
                for i, c in enumerate(row)
            )
            trs.append(f"<tr>{tds}</tr>")
        rows_html.append(
            "<table><thead><tr>"
            "<th>suite</th><th>passed</th><th>failed</th><th>skipped</th>"
            "<th>total</th><th>status</th><th>duration</th><th>cycles</th>"
            "</tr></thead><tbody>" + "".join(trs) + "</tbody></table>"
        )

        cases = case_rows(rec)
        if cases:
            n_pass = sum(1 for c in cases if c["status"] == "PASS")
            n_fail = sum(1 for c in cases if c["status"] in ("FAIL", "TIMEOUT", "ERROR"))
            n_skip = len(cases) - n_pass - n_fail
            durs = [c["duration_s"] for c in cases if isinstance(c["duration_s"], (int, float)) and c["duration_s"] > 0]
            maxd = max(durs) if durs else 0
            cts = []
            for c in cases:
                st = c["status"]
                cls = "ok" if st == "PASS" else ("bad" if st in ("FAIL", "TIMEOUT", "ERROR") else "skip")
                dur = c["duration_s"]
                dur_s = fmt_dur(dur) if isinstance(dur, (int, float)) else "-"
                if dur and maxd:
                    pct = max(3, int(dur / maxd * 100))
                    bar_cls = "bar" if st == "PASS" else "bar bar-bad"
                    bar = f'<div class="{bar_cls}" style="width:{pct}%"></div>'
                else:
                    bar = ""
                cts.append(
                    f"<tr>"
                    f"<td>{html.escape(c['suite'])}</td>"
                    f"<td><code>{html.escape(c['name'])}</code></td>"
                    f'<td class="{cls}">{html.escape(st)}</td>'
                    f"<td>{dur_s}</td>"
                    f'<td class="bar-cell">{bar}</td>'
                    f"</tr>"
                )
            rows_html.append(
                f"<h3>Cases &nbsp;<span class='count ok'>{n_pass} pass</span> · "
                f"<span class='count bad'>{n_fail} fail</span> · "
                f"<span class='count skip'>{n_skip} skip</span></h3>"
                "<table><thead><tr><th>suite</th><th>case</th><th>status</th><th>duration</th><th>relative</th></tr></thead><tbody>"
                + "".join(cts) + "</tbody></table>"
            )

        fl = failures(rec, known_sigs)
        if fl:
            items = "".join(
                f"<li><code>{html.escape(f['suite'])}/{html.escape(f['case'])}</code>"
                + (f" — <strong>known</strong>: {html.escape(f['known'])}" if f["known"] else "")
                + "</li>"
                for f in fl
            )
            rows_html.append(f"<h3>Failures</h3><ul>{items}</ul>")

        trows = timing_rows(rec)
        trs = "".join(
            "<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r) + "</tr>" for r in trows
        )
        rows_html.append(
            "<h3>Timing</h3>"
            "<table><thead><tr><th>suite</th><th>cases</th><th>duration</th><th>min</th><th>p50</th><th>p99</th><th>max</th></tr></thead><tbody>"
            + trs + "</tbody></table>"
        )

        prows = perf_rows(rec)
        if prows:
            ptrs = "".join(
                "<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r) + "</tr>" for r in prows
            )
            rows_html.append(
                "<h3>Performance (CA metrics)</h3>"
                "<table><thead><tr><th>suite</th><th>EX</th><th>SU</th><th>LD</th><th>ST</th><th>pred</th><th>scalar</th><th>dma</th><th>dual</th><th>stalls</th><th>max_stall</th><th>IPC</th><th>EX-IPC</th><th>vf_real</th></tr></thead><tbody>"
                + ptrs + "</tbody></table>"
            )

        crows = command_rows(rec)
        ctrs = []
        for r in crows:
            name, exit_code, logpath, cmd = r
            logname = Path(logpath).name if logpath else ""
            logcell = f'<a href="{html.escape(logname)}">{html.escape(logpath)}</a>' if logpath else "-"
            ctrs.append(
                f"<tr><td>{html.escape(name)}</td><td>{html.escape(exit_code)}</td>"
                f"<td>{logcell}</td><td>{html.escape(cmd)}</td></tr>"
            )
        rows_html.append(
            "<h3>Commands &amp; logs</h3>"
            "<table><thead><tr><th>suite</th><th>exit</th><th>log</th><th>command</th></tr></thead><tbody>"
            + "".join(ctrs) + "</tbody></table>"
        )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Regression Report</title>
<style>
body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 2rem; color: #1a1a1a; }}
table {{ border-collapse: collapse; margin: 1rem 0; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 0.4rem 0.6rem; text-align: left; }}
th {{ background: #f5f5f5; }}
td.ok {{ color: #0a7d33; font-weight: 600; }}
td.bad {{ color: #b00020; font-weight: 600; }}
td.skip {{ color: #888; }}
.bar-cell {{ min-width: 120px; width: 30%; }}
.bar {{ background: #0a7d33; height: 0.6em; border-radius: 3px; }}
.bar-bad {{ background: #b00020; }}
.count {{ font-weight: 600; margin-right: 0.75em; }}
.count.ok {{ color: #0a7d33; }}
.count.bad {{ color: #b00020; }}
.count.skip {{ color: #888; }}
.meta {{ color: #555; }}
h2 {{ margin-top: 2rem; }}
h3 {{ margin-top: 1rem; }}
</style></head><body>
<h1>Regression Report</h1>
{''.join(rows_html)}
</body></html>"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render run records to Markdown + HTML.")
    ap.add_argument("--run", action="append", help="run.json (repeatable); default = latest run.")
    ap.add_argument("--out", help="Output base path (writes <out>.md and <out>.html); default = alongside the run.")
    ap.add_argument("--known", help="Optional known-failures markdown used to annotate failures.")
    ap.add_argument("--open", action="store_true", help="Open the HTML in a browser after writing.")
    args = ap.parse_args(argv)

    if args.run:
        runs = args.run
    else:
        latest = _runs.latest_run()
        if not latest:
            print("No runs found under reports/. Pass --run <path>.", file=sys.stderr)
            return 1
        runs = [str(latest[0])]

    if not args.out:
        base = Path(runs[0]).parent / "report"
    else:
        base = Path(args.out)

    records = [load(r) for r in runs]
    known_sigs = load_known_signatures(args.known)
    base.parent.mkdir(parents=True, exist_ok=True)
    (Path(str(base) + ".md")).write_text(render_md(records, known_sigs), encoding="utf-8")
    html_path = Path(str(base) + ".html")
    html_path.write_text(render_html(records, known_sigs), encoding="utf-8")
    print(f"Wrote {base}.md and {html_path}")

    if args.open:
        err = _browser.open_browser(html_path)
        if err:
            print(err, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())