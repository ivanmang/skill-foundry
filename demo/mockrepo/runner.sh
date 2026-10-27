#!/usr/bin/env bash
# Mock gtest runner for the harness demo. Deterministic output: 2 pass, 1 fail.
set -u

echo "[ RUN      ] VecOpTest.case_add_128x128"
echo "[       OK ] VecOpTest.case_add_128x128 (4 ms)"
echo "[ RUN      ] VecOpTest.case_vcvt_bf16fp16_128x128"
echo "device vcvt round-field mismatch: expected round-to-nearest-even, got round-away"
echo "[  FAILED  ] VecOpTest.case_vcvt_bf16fp16_128x128 (2 ms)"
echo "[ RUN      ] ReduceTest.case_vcgmax_256"
echo "[       OK ] ReduceTest.case_vcgmax_256 (6 ms)"
echo "[==========] 3 tests from 2 test suites ran."
echo "[  PASSED  ] 2 tests."
echo "[  FAILED  ] 1 test, listed below:"
echo "[  FAILED  ] VecOpTest.case_vcvt_bf16fp16_128x128"
echo ""
echo " 1 FAILED TEST"

exit 1