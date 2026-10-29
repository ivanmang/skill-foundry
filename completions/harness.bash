# Bash tab-completion for ./harness
#
# Install (add to ~/.bashrc):
#   source /path/to/regression-harness/completions/harness.bash
#
# Then: ./harness <TAB>
_HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

_harness_complete() {
    local cur prev
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    local cmds="run report review teach promote capture-skill promote-skill skills baseline history clean open validate status diagnose targets onboarding tui menu guide demo list cann selfcheck help version"
    local opts_run="--target --suite --all-suites --testcase --filter --quiet --tui --json --dry-run --parallel --list --format --run-id --config --arches"
    local opts_promote="--propose --apply --branch --pr --root --learnings"
    local opts_report="--run --known --out --open"
    local opts_review="--run --baseline --out"
    local opts_teach="--edit --category --context --skill --wrong --correct --action --file --id --dry-run"
    local opts_clean="--dry-run --keep"
    local opts_history="--limit --json"
    local opts_status="--json --target"
    local opts_diagnose="--json --strict"
    local opts_targets="--json"
    local opts_capture_skill="--description --dry-run"
    local opts_promote_skill="--propose --apply --pr"
    local opts_skills="--search --inbox --refresh --json --install --uninstall"
    local fmts="text markdown html"

    if [[ $COMP_CWORD -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "$cmds" -- "$cur") )
        return 0
    fi

    # dynamic value completion for run --suite / --testcase
    if [[ "${COMP_WORDS[1]}" == "run" ]]; then
        if [[ "$prev" == "--format" ]]; then COMPREPLY=( $(compgen -W "$fmts" -- "$cur") ); return 0; fi
        if [[ "$prev" == "--suite" ]]; then
            COMPREPLY=( $(compgen -W "$("$_HARNESS_DIR/harness" __complete suites 2>/dev/null)" -- "$cur") ); return 0
        fi
        if [[ "$prev" == "--testcase" ]]; then
            local tc_suite=""
            local i
            for ((i=1; i<COMP_CWORD; i++)); do
                if [[ "${COMP_WORDS[i]}" == "--suite" && $((i+1)) -lt COMP_CWORD ]]; then tc_suite="${COMP_WORDS[i+1]}"; fi
            done
            if [[ -n "$tc_suite" ]]; then
                COMPREPLY=( $(compgen -W "$("$_HARNESS_DIR/harness" __complete testcases "$tc_suite" 2>/dev/null)" -- "$cur") )
            fi
            return 0
        fi
        COMPREPLY=( $(compgen -W "$opts_run" -- "$cur") )
        return 0
    fi

    case "${COMP_WORDS[1]}" in
        promote) COMPREPLY=( $(compgen -W "$opts_promote" -- "$cur") ) ;;
        capture-skill) COMPREPLY=( $(compgen -W "$opts_capture_skill" -- "$cur") ) ;;
        promote-skill) COMPREPLY=( $(compgen -W "$opts_promote_skill" -- "$cur") ) ;;
        skills) COMPREPLY=( $(compgen -W "$opts_skills" -- "$cur") ) ;;
        report)  COMPREPLY=( $(compgen -W "$opts_report" -- "$cur") ) ;;
        review)  COMPREPLY=( $(compgen -W "$opts_review" -- "$cur") ) ;;
        teach)   COMPREPLY=( $(compgen -W "$opts_teach" -- "$cur") ) ;;
        clean)   COMPREPLY=( $(compgen -W "$opts_clean" -- "$cur") ) ;;
        history) COMPREPLY=( $(compgen -W "$opts_history" -- "$cur") ) ;;
        status)  COMPREPLY=( $(compgen -W "$opts_status" -- "$cur") ) ;;
        diagnose) COMPREPLY=( $(compgen -W "$opts_diagnose" -- "$cur") ) ;;
        targets)  COMPREPLY=( $(compgen -W "$opts_targets" -- "$cur") ) ;;
        list)
            if [[ "$prev" == "--format" ]]; then COMPREPLY=( $(compgen -W "$fmts" -- "$cur") ); return 0; fi
            COMPREPLY=( $(compgen -W "--target --format --config --arches" -- "$cur") ) ;;
        *) COMPREPLY=() ;;
    esac
    return 0
}

complete -F _harness_complete harness
complete -F _harness_complete ./harness