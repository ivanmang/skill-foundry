#!/usr/bin/env python3
"""Shared terminal helpers: ANSI colors, c(), mark(), fmt_dur().

Internal — imported by the CLI scripts so the color/duration logic isn't
copy-pasted everywhere.
"""

from __future__ import annotations

import sys

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"


def c(text: str, color: str) -> str:
    """Colorize `text` with `color`, stripping color when not a TTY."""
    return f"{color}{text}{RESET}" if sys.stdout.isatty() else text


def mark(ok: bool) -> str:
    return c("✓" if ok else "✗", GREEN if ok else RED)


def fmt_dur(sec: float | None) -> str:
    if sec is None:
        return "-"
    if sec < 1:
        return f"{sec * 1000:.0f}ms"
    return f"{sec:.2f}s"
