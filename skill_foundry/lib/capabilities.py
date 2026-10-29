#!/usr/bin/env python3
"""Runtime capability checks — determine what can actually run on this machine.

These are used by run.py to auto-derive which suites are runnable in the
current environment (compiler, CANN, simulator, device, MPI), independent of the
static `enabled` flag in config/suites.json.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[2]
_CACHE_FILE = HARNESS / ".cache" / "cann-lanes.json"
_CACHE_TTL = 300  # seconds; headers/simulators change rarely, but a re-scan is cheap


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


_CANN_LANES_CACHE: tuple[set[str], set[str]] | None = None


def _load_cache() -> dict:
    try:
        return json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(data: dict) -> None:
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


def _toolkit_lanes() -> tuple[set[str], set[str]]:
    """(headers, simulators) arch sets for the current ASCEND_HOME_PATH CANN."""
    global _CANN_LANES_CACHE
    if _CANN_LANES_CACHE is not None:
        return _CANN_LANES_CACHE
    home = Path(os.environ.get("ASCEND_HOME_PATH", ""))
    if not home:
        _CANN_LANES_CACHE = (set(), set())
        return _CANN_LANES_CACHE

    # persistent cross-process cache (TTL) so status/list are instant on slow mounts
    key = str(home)
    cached = _load_cache().get(key)
    if cached and (time.time() - cached.get("ts", 0)) < _CACHE_TTL:
        _CANN_LANES_CACHE = (set(cached.get("headers", [])), set(cached.get("simulators", [])))
        return _CANN_LANES_CACHE

    try:
        from skill_foundry.lib import cann as detect_cann
        info = detect_cann.analyze(home, detect_cann.load_config())
        _CANN_LANES_CACHE = (set(info["headers"]), set(info["simulators"]))
        data = _load_cache()
        data[key] = {
            "ts": time.time(),
            "headers": sorted(_CANN_LANES_CACHE[0]),
            "simulators": sorted(_CANN_LANES_CACHE[1]),
        }
        _save_cache(data)
    except Exception:
        _CANN_LANES_CACHE = (set(), set())
    return _CANN_LANES_CACHE


def suite_reason(suite: dict, arches: dict) -> tuple[bool, str]:
    """Return (runnable, why-not) for a suite in the current environment."""
    mode = (suite.get("mode") or "").lower()

    if mode == "cpu":
        return (has_compiler(), "needs clang++>=15 or g++>=13")

    if mode == "npu-sim":
        if not has_ascend():
            return (False, "ASCEND_HOME_PATH not set")
        arch = suite.get("arch") or ""
        arch_info = arches.get(arch, {})
        soc = arch_info.get("soc", "")
        headers, sims = _toolkit_lanes()
        missing = []
        if arch not in headers:
            missing.append("compile headers")
        if arch not in sims:
            missing.append(f"simulator {soc or arch}")
        if missing:
            return (False, "CANN lacks " + " + ".join(missing))
        return (True, "ok")

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