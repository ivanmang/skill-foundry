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

from skill_foundry.paths import ROOT as HARNESS  # noqa: E402
_CACHE_FILE = HARNESS / ".cache" / "cann-lanes.json"
_CACHE_TTL = 300  # seconds; headers/simulators change rarely, but a re-scan is cheap
_UNSET = object()


def _which(name: str) -> str | None:
    return shutil.which(name)


def _compiler_version(name: str) -> tuple[int, int] | None:
    """Return (major, minor) for a compiler on PATH, or None if undetectable."""
    p = _which(name)
    if not p:
        return None
    try:
        if name in ("g++", "gcc"):
            # gcc --version omits the word "version"; -dumpfullversion is parseable.
            out = subprocess.run([p, "-dumpfullversion"], capture_output=True, text=True, timeout=20).stdout
            m = re.search(r"(\d+)\.(\d+)", out)
        else:
            out = subprocess.run([p, "--version"], capture_output=True, text=True, timeout=20).stdout
            m = re.search(r"version\s+(\d+)\.?(\d*)", out)
    except Exception:
        return None
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2) or 0))


def has_compiler(min_clang: int = 15, min_gcc: int = 13) -> bool:
    for name, kind in (("clang++", "clang"), ("g++", "gcc")):
        v = _compiler_version(name)
        if v is None:
            continue
        major = v[0]
        if (kind == "clang" and major >= min_clang) or (kind == "gcc" and major >= min_gcc):
            return True
    return False


def has_ascend() -> bool:
    return bool(os.environ.get("ASCEND_HOME_PATH"))


_ENV_SH_ASCEND_CACHE: str | object | None = _UNSET


def env_sh_ascend() -> str | None:
    """The ASCEND_HOME_PATH that env.sh would export, if env.sh exists (else None)."""
    global _ENV_SH_ASCEND_CACHE
    if _ENV_SH_ASCEND_CACHE is not _UNSET:
        return _ENV_SH_ASCEND_CACHE  # type: ignore[return-value]
    value: str | None = None
    try:
        text = (HARNESS / "env.sh").read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#") or "ASCEND_HOME_PATH" not in s:
            continue
        m = re.search(r'ASCEND_HOME_PATH\s*=\s*"?([^"\s]+)"?', s)
        if m:
            candidate = m.group(1)
            # skip unresolved shell-expansion placeholders (e.g. env.example.sh's
            # `${ASCEND_HOME_PATH:-}`) — only a concrete path is useful.
            if candidate and "$" not in candidate:
                value = candidate
            break
    _ENV_SH_ASCEND_CACHE = value
    return value


def ascend_state() -> tuple[str, str]:
    """(state, path) for ASCEND_HOME_PATH.

    'sourced' — the env var is set; 'envsh' — env.sh sets it but it isn't
    sourced yet; 'none' — no ASCEND_HOME_PATH anywhere.
    """
    env = os.environ.get("ASCEND_HOME_PATH")
    if env:
        return ("sourced", env)
    from_sh = env_sh_ascend()
    if from_sh:
        return ("envsh", from_sh)
    return ("none", "")


def _ascend_missing_reason() -> str:
    """Why ASCEND_HOME_PATH isn't usable right now (env.sh hint when relevant)."""
    state, _path = ascend_state()
    if state == "envsh":
        return "env.sh present but not sourced — run `source ./env.sh`"
    return "ASCEND_HOME_PATH not set"


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
            return (False, _ascend_missing_reason())
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
            return (False, _ascend_missing_reason())
        ok = has_hardware()
        return (ok, "no NPU device (npu-smi failed)" if not ok else "ok")

    if mode == "costmodel":
        if not has_ascend():
            return (False, _ascend_missing_reason())
        return (True, "ok")

    if mode == "comm":
        if not has_ascend():
            return (False, _ascend_missing_reason())
        ok = has_mpi()
        return (ok, "mpirun not found" if not ok else "ok")

    # static / mock / unknown: always runnable
    return (True, "ok")