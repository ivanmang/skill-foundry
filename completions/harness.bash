# Bash tab-completion for ./harness
#
# Install (add to ~/.bashrc):
#   source /path/to/regression-harness/completions/harness.bash
#
# Then: ./harness <TAB>

_harness_complete() {
    local cur prev
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    local cmds="run report review teach promote baseline guide demo list selfcheck help version"
    local opts_run="--target --suite --all-suites --quiet --tui --json --list --format --run-id --config --arches"
    local opts_promote="--propose --apply --branch --pr --root --learnings"
    local opts_report="--run --known --out"
    local opts_review="--run --baseline --out"
    local opts_teach="--edit --category --context --skill --wrong --correct --action --file --id --dry-run"
    local fmts="text markdown html"

    if [[ $COMP_CWORD -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "$cmds" -- "$cur") )
        return 0
    fi

    case "${COMP_WORDS[1]}" in
        run)
            if [[ "$prev" == "--format" ]]; then COMPREPLY=( $(compgen -W "$fmts" -- "$cur") ); return 0; fi
            COMPREPLY=( $(compgen -W "$opts_run" -- "$cur") ) ;;
        promote) COMPREPLY=( $(compgen -W "$opts_promote" -- "$cur") ) ;;
        report)  COMPREPLY=( $(compgen -W "$opts_report" -- "$cur") ) ;;
        review)  COMPREPLY=( $(compgen -W "$opts_review" -- "$cur") ) ;;
        teach)   COMPREPLY=( $(compgen -W "$opts_teach" -- "$cur") ) ;;
        list)
            if [[ "$prev" == "--format" ]]; then COMPREPLY=( $(compgen -W "$fmts" -- "$cur") ); return 0; fi
            COMPREPLY=( $(compgen -W "--target --format --config --arches" -- "$cur") ) ;;
        *) COMPREPLY=() ;;
    esac
    return 0
}

complete -F _harness_complete harness
complete -F _harness_complete ./harness