# Machine-local environment for the skill-foundry.
#
# Copy this to env.sh (gitignored) and edit for your machine, then:
#   source ./env.sh
#
# The regression workflow scripts need ASCEND_HOME_PATH only for npu-sim / npu /
# costmodel / comm suites; cpu-st and static suites run without it.

# CANN toolkit root (points at set_env.sh). Example:
#   export ASCEND_HOME_PATH="$HOME/Ascend/cann-9.0.0-alpha.1"
export ASCEND_HOME_PATH="${ASCEND_HOME_PATH:-}"

# Optional: pto-isa checkout used by the harness (default ~/pto-isa).
#   export PTO_ISA_REPO="$HOME/pto-isa"
export PTO_ISA_REPO="${PTO_ISA_REPO:-$HOME/pto-isa}"

# Per-target checkout env vars (each target declares its own repo_env in
# config/suites.json). Example for the pto-vmi target:
#   export PTO_VMI_REPO="$HOME/pto-vmi"

# Optional: GitHub personal access token — lets `./harness promote --pr`
# auto-create the pull request (`gh pr create` / GitHub REST).
# If unset, --pr still pushes the branch but only prints the PR-new URL.
#   export GH_TOKEN="<your token>"        # GitHub: Settings → Developer settings → PAT
# GitCode (legacy fallback): export GITCODE_TOKEN="<token>"   # gitcode: Settings → Access Tokens
