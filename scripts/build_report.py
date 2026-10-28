#!/usr/bin/env python3
"""Turn run record(s) into Markdown + self-contained HTML reports.

Usage:
  python3 scripts/build_report.py --run reports/<id>/run.json --out reports/<id>/report
  python3 scripts/build_report.py --run a.json --run b.json --out combined/report

Optionally annotate failures against a known-failures file (the triage corpus
kept by the harness). Pass --known to mark matched failures as known:

  python3 scripts/build_report.py --run reports/<id>/run.json \
      --known .claude/skills/pto-isa/references/known-failures.md \
      --out reports/<id>/report
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _runs  # noqa: E402
import _browser  # noqa: E402

HARNESS = Path(__file__).resolve().parent.parent


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


def fmt_dur(sec: float | None) -> str:
    if sec is None:
        return "-"
    if sec < 1:
        return f"{sec * 1000:.0f}ms"
    return f"{sec:.2f}s"


def suite_rows(record: dict) -> list[list[str]]:
    rows = []
    for s in record.get("suites", []):
        r = s.get("results") or {}
        sm = r.get("summary") or {}
        rows.append([
            s.get("name", "?"),
            str(sm.get("passed", 0)),
            str(sm.get("failed", 0)),
            str(sm.get("skipped", 0)),
            str(sm.get("total", 0)),
            s.get("status", "UNKNOWN"),
            fmt_dur(s.get("duration_s")),
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
        lines += [
            f"## Run: {rec.get('run_id')}",
            "",
            f"- target: `{rec.get('target')}`  repo: `{rec.get('target_repo')}`",
            f"- target commit: `{rec.get('target_commit')}`  dirty: {rec.get('target_dirty')}",
            f"- host: `{rec.get('host')}`  generated: {rec.get('generated_at')}",
            "",
            "| suite | passed | failed | skipped | total | status | duration |",
            "|---|---|---|---|---|---|---|",
        ]
        for row in suite_rows(rec):
            lines.append("| " + " | ".join(row) + " |")
        fl = failures(rec, known_sigs)
        if fl:
            lines += _failures_md(fl)
        lines += ["", "---", ""]
    return "\n".join(lines)


def render_html(records: list[dict], known_sigs: list[str]) -> str:
    rows_html = []
    for rec in records:
        rows_html.append(
            f'<h2>Run: {html.escape(rec.get("run_id", ""))}</h2>'
            f'<p class="meta">target <code>{html.escape(rec.get("target", ""))}</code> · '
            f'commit <code>{html.escape(rec.get("target_commit", "") or "")}</code> · '
            f'host <code>{html.escape(rec.get("host", ""))}</code></p>'
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
            "<th>total</th><th>status</th><th>duration</th>"
            "</tr></thead><tbody>" + "".join(trs) + "</tbody></table>"
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
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Regression Report</title>
<style>
body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 2rem; color: #1a1a1a; }}
table {{ border-collapse: collapse; margin: 1rem 0; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 0.4rem 0.6rem; text-align: left; }}
th {{ background: #f5f5f5; }}
td.ok {{ color: #0a7d33; font-weight: 600; }}
td.bad {{ color: #b00020; font-weight: 600; }}
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