#!/usr/bin/env python3
"""Runtime capability checks — determine what can actually run on this machine.

These are used by run_suite.py to auto-derive which suites are runnable in the
current environment (compiler, CANN, simulator, device, MPI), independent of the
static `enabled` flag in config/suites.json.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path


def _which(name: str) -> str | None:
    return shutil.which(name)


def has_compiler(min_clang: int = 15, min_gcc: int = 13) -> bool:
    for name, kind in (("clang++", "clang"), ("g++", "gcc")):
        p = _which(name)
        if not p:
            continue
        try:
            out = subprocess.run([p, "--version"], capture_output=True, text=True, timeout=20).stdout
        except Exception:
            continue
        m = re.search(r"version\s+(\d+)", out)
        if m and ((kind == "clang" and int(m.group(1)) >= min_clang)
                  or (kind == "gcc" and int(m.group(1)) >= min_gcc)):
            return True
    return False


def has_ascend() -> bool:
    return bool(os.environ.get("ASCEND_HOME_PATH"))


def _simulator_dirs() -> list[Path]:
    home = Path(os.environ.get("ASCEND_HOME_PATH", ""))
    if not home:
        return []
    return [home / "x86_64-linux" / "simulator", home / "tools" / "simulator"]


def has_simulator(soc: str) -> bool:
    if not soc:
        return False
    return any((base / soc).exists() for base in _simulator_dirs())


def has_hardware() -> bool:
    npu_smi = _which("npu-smi")
    if not npu_smi:
        return False
    try:
        r = subprocess.run([npu_smi, "info"], capture_output=True, timeout=30)
        return r.returncode == 0
    except Exception:
        return False


def has_mpi() -> bool:
    return _which("mpirun") is not None


def suite_reason(suite: dict, arches: dict) -> tuple[bool, str]:
    """Return (runnable, why-not) for a suite in the current environment."""
    mode = (suite.get("mode") or "").lower()

    if mode == "cpu":
        return (has_compiler(), "needs clang++>=15 or g++>=13")

    if mode == "npu-sim":
        if not has_ascend():
            return (False, "ASCEND_HOME_PATH not set")
        arch = arches.get(suite.get("arch") or "", {})
        soc = arch.get("soc", "")
        if not soc:
            return (False, "no soc in config/arches.json")
        ok = has_simulator(soc)
        return (ok, f"CANN simulator {soc} not found" if not ok else "ok")

    if mode == "npu":
        if not has_ascend():
            return (False, "ASCEND_HOME_PATH not set")
        ok = has_hardware()
        return (ok, "no NPU device (npu-smi failed)" if not ok else "ok")

    if mode == "costmodel":
        if not has_ascend():
            return (False, "ASCEND_HOME_PATH not set")
        return (True, "ok")

    if mode == "comm":
        if not has_ascend():
            return (False, "ASCEND_HOME_PATH not set")
        ok = has_mpi()
        return (ok, "mpirun not found" if not ok else "ok")

    # static / mock / unknown: always runnable
    return (True, "ok")