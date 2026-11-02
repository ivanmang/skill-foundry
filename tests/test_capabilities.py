#!/usr/bin/env python3
"""Guard the compiler detection in capabilities.has_compiler().

Regressions here are subtle: the gcc/g++ branch once used `--version` + a
`version\\s+(\\d+)` regex, but `g++ --version` omits the word "version", so every
gcc-only machine was misdetected as "no compiler". These tests pin both the
gcc (via -dumpfullversion) and clang (via --version) paths.
"""

from __future__ import annotations

import unittest
from unittest import mock

from skill_foundry.lib import capabilities


def _mk_subprocess(stdout: str):
    return mock.patch.object(
        capabilities.subprocess, "run",
        return_value=mock.Mock(stdout=stdout),
    )


class HasCompilerTest(unittest.TestCase):
    def test_gcc13_detected(self):
        with mock.patch.object(capabilities, "_which", side_effect=lambda n: "/usr/bin/g++" if n == "g++" else None), \
             _mk_subprocess("13.3.0\n"):
            self.assertTrue(capabilities.has_compiler())

    def test_gcc12_rejected(self):
        with mock.patch.object(capabilities, "_which", side_effect=lambda n: "/usr/bin/g++" if n == "g++" else None), \
             _mk_subprocess("12.2.0\n"):
            self.assertFalse(capabilities.has_compiler())

    def test_gcc13_gcc_detected(self):
        # bare `gcc` also qualifies when g++ is absent
        with mock.patch.object(capabilities, "_which", side_effect=lambda n: "/usr/bin/gcc" if n == "g++" or n == "gcc" else None), \
             _mk_subprocess("13.1.0\n"):
            self.assertTrue(capabilities.has_compiler())

    def test_clang15_detected(self):
        with mock.patch.object(capabilities, "_which", side_effect=lambda n: "/usr/bin/clang++" if n == "clang++" else None), \
             _mk_subprocess("Ubuntu clang version 15.0.7-1ubuntu2\n"):
            self.assertTrue(capabilities.has_compiler())

    def test_clang14_rejected(self):
        with mock.patch.object(capabilities, "_which", side_effect=lambda n: "/usr/bin/clang++" if n == "clang++" else None), \
             _mk_subprocess("Ubuntu clang version 14.0.0\n"):
            self.assertFalse(capabilities.has_compiler())

    def test_no_compiler(self):
        with mock.patch.object(capabilities, "_which", return_value=None):
            self.assertFalse(capabilities.has_compiler())


if __name__ == "__main__":
    unittest.main()