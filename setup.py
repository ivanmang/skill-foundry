#!/usr/bin/env python3
"""Compatibility shim so ``pip install -e .`` works when the build backend lacks
PEP 660 editable support (the error pip prints when only ``pyproject.toml`` is
present). Canonical metadata stays in ``pyproject.toml`` (PEP 621); setuptools
reads it from here via ``setup()``.
"""

from setuptools import setup

setup()
