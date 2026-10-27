# Machine-local environment for the regression harness.
#
# Copy this to env.sh (gitignored) and edit for your machine, then:
#   source ./env.sh
#
# The harness needs ASCEND_HOME_PATH only for npu-sim / npu / costmodel / comm
# suites; cpu-st and static suites run without it.

# CANN toolkit root (points at set_env.sh). Example:
#   export ASCEND_HOME_PATH="$HOME/Ascend/cann-9.0.0-alpha.1"
export ASCEND_HOME_PATH="${ASCEND_HOME_PATH:-}"

# Optional: pto-isa checkout used by the harness (default ~/pto-isa).
#   export PTO_ISA_REPO="$HOME/pto-isa"
export PTO_ISA_REPO="${PTO_ISA_REPO:-$HOME/pto-isa}"
