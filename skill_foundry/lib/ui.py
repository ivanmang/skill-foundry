"""Shared interactive terminal helpers: arrow-key menus, prompts, pickers.

Imported by the CLI shell (menu, wrap) and the workflow tours (guide, demo,
onboarding). Colors/`c()` are re-exported from `lib/term.py` (single source).
"""

from __future__ import annotations

import os
import re
import select
import sys
import termios
import time
import tty
from pathlib import Path

from skill_foundry.lib import cann as detect_cann
from skill_foundry.lib.term import GREEN, RED, YELLOW, BOLD, RESET, c  # noqa: F401 (re-export)


def banner(title: str) -> None:
    print(f"\n{c('══ ' + title + ' ' + '═' * (50 - len(title)), BOLD)}")


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        try:
            val = input(f"  {prompt}{suffix}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if val:
            return val
        if default:
            return default
        return ""


def ask_yesno(prompt: str, default: str = "n") -> bool:
    suffix = "Y/n" if default == "y" else "y/N"
    while True:
        v = ask(f"{prompt} ({suffix})", default).lower()
        if v in ("y", "yes"):
            return True
        if v in ("n", "no"):
            return False


def _read_key() -> str:
    """Read one keypress in raw mode (arrow keys, Enter, q, Ctrl-C)."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd, termios.TCSADRAIN)
        first = os.read(fd, 1)
        if not first:
            return ""
        if first == b"\x1b":
            seq = b""
            deadline = time.time() + 0.08
            while len(seq) < 2 and time.time() < deadline:
                r, _, _ = select.select([fd], [], [], 0.02)
                if not r:
                    break
                seq += os.read(fd, 1)
            mapping = {
                "[A": "UP",
                "[B": "DOWN",
                "[C": "RIGHT",
                "[D": "LEFT",
                "OA": "UP",
                "OB": "DOWN",
                "OC": "RIGHT",
                "OD": "LEFT",
            }
            return mapping.get(seq.decode("latin-1"), "ESC")
        if first in (b"\r", b"\n"):
            return "ENTER"
        if first in (b"q", b"Q"):
            return "q"
        if first == b"\x03":
            return "CTRL_C"
        return first.decode("latin-1")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def select_menu(title: str, options: list, default_index: int = 0, height: int = 12):
    """Arrow-key menu; options = str labels or (label, value) tuples. Returns the
    value (or label when bare string). Falls back to a numbered prompt on non-TTY."""
    if not options:
        return None
    labels = [o[0] if isinstance(o, tuple) else o for o in options]
    values = [o[1] if isinstance(o, tuple) else o for o in options]

    if not sys.stdin.isatty():
        print(c(title, BOLD))
        for i, lab in enumerate(labels, 1):
            print(f"  {i}) {lab}")
        choice = ask("Choose [1-%d] or name (Enter = skip)" % len(labels))
        if choice.isdigit() and 1 <= int(choice) <= len(labels):
            return values[int(choice) - 1]
        low = choice.lower()
        for i, v in enumerate(values):
            if v is not None and str(v).lower() == low:
                return v
        return None

    idx = max(0, min(default_index, len(labels) - 1))
    n = len(labels)
    visible = min(n, height)
    top = 0

    def render() -> str:
        nonlocal top
        if idx < top:
            top = idx
        elif idx >= top + visible:
            top = idx - visible + 1
        top = max(0, min(top, n - visible))
        lines = []
        for i in range(visible):
            j = top + i
            lab = labels[j]
            if j == idx:
                lines.append("  \033[7m ▶ " + lab + " \033[0m\033[K")
            else:
                lines.append("    " + lab + " \033[K")
        return "\n".join(lines)

    sys.stdout.write(c(title, BOLD) + "\n")
    sys.stdout.write(render() + "\n")

    while True:
        key = _read_key()
        if key == "UP":
            idx = (idx - 1) % n
        elif key == "DOWN":
            idx = (idx + 1) % n
        elif key == "ENTER":
            return values[idx]
        elif key in ("q", "ESC", "CTRL_C"):
            sys.stdout.write("\n")
            return None
        elif isinstance(key, str) and key.isdigit():
            di = int(key) - 1
            if 0 <= di < n:
                idx = di
            else:
                continue
        else:
            continue
        sys.stdout.write(f"\033[{visible}A\r")
        sys.stdout.write(render() + "\n")


def choose_cann() -> str | None:
    """List installed CANN toolkits with arch support and let the user pick one."""
    cfg = detect_cann.load_config()
    roots = [r for r in detect_cann.candidates() if detect_cann.looks_like_toolkit(r)]
    if not roots:
        return None
    infos = [detect_cann.analyze(r, cfg) for r in roots]
    options = []
    for info in infos:
        hdr = " ".join(info["headers"]) if info["headers"] else "-"
        sim = " ".join(info["simulators"]) if info["simulators"] else "-"
        label = f"{info['path']}  ·  v{info['version']}  ·  headers {hdr}  ·  sim {sim}"
        options.append((label, info["path"]))
    title = c(
        "  No ASCEND_HOME_PATH set. Choose a CANN package (↑/↓ + Enter, q = skip):",
        YELLOW,
    )
    return select_menu(title, options)


def choose_testcase(suite: str, tdirs: dict, repo: Path, kind: str = "dir") -> str:
    """Dropdown of testcases; '' = run all. kind: 'dir' (default) or 'file' (.py cases)."""
    rel = tdirs.get(suite)
    base = repo / rel if rel else None
    if not base or not base.exists():
        return ask("Testcase (blank = all in suite)").strip()
    if kind == "file":
        files = sorted(
            p.relative_to(base).as_posix()
            for p in base.rglob("*.py")
            if p.is_file() and "__" not in p.name
        )
        if not files:
            return ""
        options = [("all cases (no filter)", "")] + [(f, f) for f in files]
        sel = select_menu(f"Choose a case for {suite} (↑/↓ + Enter, q = all):", options)
        return sel if sel is not None else ""
    names = sorted(p.name for p in base.iterdir() if p.is_dir())
    if not names:
        return ""
    options = [("all testcases", "")] + [(name, name) for name in names]
    sel = select_menu("Choose a testcase (↑/↓ + Enter, q = all):", options)
    return sel if sel is not None else ""


GTEST_RE = re.compile(r"TEST(?:_F|_P)?\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)")


def choose_filter(suite: str, testcase: str, tdirs: dict, repo: Path) -> str:
    """Dropdown of gtest cases in the chosen testcase; '' = no filter."""
    rel = tdirs.get(suite)
    d = repo / rel / testcase if rel else None
    main = d / "main.cpp" if d else None
    if not main or not main.exists():
        return ask("gtest filter (blank = none)").strip()
    text = main.read_text(encoding="utf-8", errors="replace")
    cases = sorted({f"{m.group(1)}.{m.group(2)}" for m in GTEST_RE.finditer(text)})
    if not cases:
        return ask("gtest filter (blank = none)").strip()
    options = [("all cases (no filter)", "")] + [(c, c) for c in cases]
    sel = select_menu(
        f"Choose a filter for {testcase} (↑/↓ + Enter, q = all):", options
    )
    return sel if sel is not None else ""
