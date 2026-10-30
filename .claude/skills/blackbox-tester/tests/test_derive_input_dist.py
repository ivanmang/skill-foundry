#!/usr/bin/env python3
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.
"""derive_input_dist 推导回归测试。"""

import pytest

import derive_input_dist as dut


def test_any_normal_nested_dict():
    assert dut._any_normal({"inputs": [{"data_distribution": "normal"}]}) is True


def test_any_normal_uniform_only():
    assert dut._any_normal({"inputs": [{"data_distribution": "uniform"}]}) is False


def test_main_emits_flag_for_normal(tmp_path, capsys):
    spec = tmp_path / "spec.yaml"
    spec.write_text("inputs:\n  - data_distribution: normal\n", encoding="utf-8")
    assert dut.main(["--spec", str(spec)]) == 0
    assert capsys.readouterr().out.strip() == "--input-dist normal"


def test_main_empty_when_no_normal(tmp_path, capsys):
    spec = tmp_path / "spec.yaml"
    spec.write_text("inputs:\n  - data_distribution: uniform\n", encoding="utf-8")
    assert dut.main(["--spec", str(spec)]) == 0
    assert capsys.readouterr().out == ""


def test_main_missing_spec(tmp_path, capsys):
    assert dut.main(["--spec", str(tmp_path / "nope.yaml")]) == 1
    assert "spec not found" in capsys.readouterr().err


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))