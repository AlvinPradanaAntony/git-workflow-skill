#!/bin/sh
# Run from an extracted Linux/macOS release archive, as the current user.
set -eu

cli_bin_dir="${HOME}/.local/bin"
cli_update_path=true
cli_profile=''
while [ "$#" -gt 0 ]; do
    case "$1" in
        --bin-dir|--profile)
            cli_option="$1"
            [ "$#" -ge 2 ] || { printf '%s requires a path\n' "$cli_option" >&2; exit 2; }
            if [ "$cli_option" = '--bin-dir' ]; then cli_bin_dir="$2"; else cli_profile="$2"; fi
            shift 2 ;;
        --no-path-update) cli_update_path=false; shift ;;
        --help)
            printf '%s\n' 'Usage: sh install-cli.sh [--bin-dir PATH] [--profile PATH] [--no-path-update]'
            exit 0 ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
    esac
done
case "$cli_bin_dir" in
    *:*|*'
'*) printf '%s\n' 'The installation directory cannot contain a colon or newline.' >&2; exit 2 ;;
esac
cli_script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
cli_source="$cli_script_dir/git-workflow"
[ -f "$cli_source" ] || { printf '%s\n' 'git-workflow must be beside this script. Extract the complete release archive first.' >&2; exit 2; }
mkdir -p -- "$cli_bin_dir"
cli_bin_dir=$(CDPATH='' cd -- "$cli_bin_dir" && pwd)
if [ "$cli_source" != "$cli_bin_dir/git-workflow" ]; then
    install -m 755 "$cli_source" "$cli_bin_dir/git-workflow"
fi

cli_register_profile() {
    cli_target_profile="$1"
    if [ ! -f "$cli_target_profile" ] || ! grep -Fqx -- "$cli_export_line" "$cli_target_profile"; then
        printf '\n# Git Workflow CLI\ncase ":$PATH:" in\n    *":%s:"*) ;;\n%s\nesac\n' \
            "$cli_escaped_dir" "$cli_export_line" >> "$cli_target_profile"
    fi
    printf 'PATH registered in %s\n' "$cli_target_profile"
}

if [ "$cli_update_path" = true ]; then
    case ":${PATH}:" in
        *":${cli_bin_dir}:"*) ;;
        *)
            # Quote shell metacharacters so a custom directory remains literal.
            cli_escaped_dir=$(printf '%s' "$cli_bin_dir" | sed 's/["\\$`]/\\&/g')
            cli_export_line="    *) export PATH=\"${cli_escaped_dir}:\$PATH\" ;;"
            if [ -n "$cli_profile" ]; then
                cli_register_profile "$cli_profile"
            else
                case "${SHELL:-/bin/sh}" in
                    */zsh|zsh) cli_register_profile "${HOME}/.zshrc" ;;
                    */bash|bash)
                        cli_register_profile "${HOME}/.bashrc"
                        if [ -f "${HOME}/.bash_profile" ]; then
                            cli_register_profile "${HOME}/.bash_profile"
                        elif [ -f "${HOME}/.bash_login" ]; then
                            cli_register_profile "${HOME}/.bash_login"
                        else
                            cli_register_profile "${HOME}/.profile"
                        fi ;;
                    */sh|sh|*/dash|dash|*/ksh|ksh) cli_register_profile "${HOME}/.profile" ;;
                    *)
                        cli_update_path=false
                        printf 'Shell %s requires manual PATH configuration; add %s using your shell configuration.\n' \
                            "${SHELL}" "$cli_bin_dir" ;;
                esac
            fi
            ;;
    esac
fi
printf 'Installed CLI: %s/git-workflow\n' "$cli_bin_dir"
if [ "$cli_update_path" = true ]; then
    printf '%s\n' 'Open a new terminal, then run: git-workflow --version'
else
    printf '%s\n' 'PATH registration skipped. Add the installation directory to PATH to use git-workflow by name.'
fi
