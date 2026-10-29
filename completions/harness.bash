# Bash tab-completion for ./harness
#
# Install (add to ~/.bashrc):
#   source /path/to/skill-foundry/completions/harness.bash
#
# Then: ./harness <TAB>
_HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

_harness_complete() {
    local cur prev
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # ./harness exposes ONLY the skill-ops loop (+ shell housekeeping).
    local cmds="capture-skill promote-skill teach promote skills menu selfcheck help version"
    local opts_promote="--propose --apply --pr --direct --review --force"
    local opts_teach="--edit --category --context --skill --wrong --correct --action --file --id --dry-run"
    local opts_capture_skill="--description --dry-run"
    local opts_promote_skill="--propose --apply --pr --direct --review --force"
    local opts_skills="--search --inbox --refresh --json --install --uninstall"

    if [[ $COMP_CWORD -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "$cmds" -- "$cur") )
        return 0
    fi

    case "${COMP_WORDS[1]}" in
        promote) COMPREPLY=( $(compgen -W "$opts_promote" -- "$cur") ) ;;
        capture-skill) COMPREPLY=( $(compgen -W "$opts_capture_skill" -- "$cur") ) ;;
        promote-skill) COMPREPLY=( $(compgen -W "$opts_promote_skill" -- "$cur") ) ;;
        skills) COMPREPLY=( $(compgen -W "$opts_skills" -- "$cur") ) ;;
        teach)  COMPREPLY=( $(compgen -W "$opts_teach" -- "$cur") ) ;;
        *) COMPREPLY=() ;;
    esac
    return 0
}

complete -F _harness_complete harness
complete -F _harness_complete ./harness