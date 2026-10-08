#!/bin/sh
# Remove the current user's native CLI; installed agent skills are retained.
set -eu

cli_bin_dir="${HOME}/.local/bin"
cli_update_path=true
cli_profile=''
cli_dry_run=false
while [ "$#" -gt 0 ]; do
    case "$1" in
        --bin-dir|--profile)
            cli_option="$1"
            [ "$#" -ge 2 ] || { printf '%s requires a path\n' "$cli_option" >&2; exit 2; }
            if [ "$cli_option" = '--bin-dir' ]; then cli_bin_dir="$2"; else cli_profile="$2"; fi
            shift 2 ;;
        --no-path-update) cli_update_path=false; shift ;;
        --dry-run) cli_dry_run=true; shift ;;
        --help)
            printf '%s\n' 'Usage: sh uninstall-cli.sh [--bin-dir PATH] [--profile PATH] [--no-path-update] [--dry-run]'
            exit 0 ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
    esac
done
case "$cli_bin_dir" in
    *:*|*'
'*) printf '%s\n' 'The installation directory cannot contain a colon or newline.' >&2; exit 2 ;;
esac
if [ -d "$cli_bin_dir" ]; then
    cli_bin_dir=$(CDPATH='' cd -- "$cli_bin_dir" && pwd)
else
    case "$cli_bin_dir" in /*) ;; *) cli_bin_dir="$(pwd)/$cli_bin_dir" ;; esac
fi
cli_executable="$cli_bin_dir/git-workflow"
if [ -e "$cli_executable" ] && [ ! -f "$cli_executable" ]; then
    printf '%s\n' 'The CLI executable path is not a file.' >&2; exit 2
fi
if [ "$cli_dry_run" = true ]; then
    printf 'Would remove CLI (if installed): %s\n' "$cli_executable"
else
    # Remove only this file, even when the bin directory contains other tools.
    rm -f -- "$cli_executable"
    printf 'Removed CLI (if installed): %s\n' "$cli_executable"
fi

cli_escaped_dir=$(printf '%s' "$cli_bin_dir" | sed 's/["\\$`]/\\&/g')
CLI_MATCH_CASE="    *\":${cli_escaped_dir}:\"*) ;;"
CLI_MATCH_EXPORT="    *) export PATH=\"${cli_escaped_dir}:\$PATH\" ;;"
export CLI_MATCH_CASE CLI_MATCH_EXPORT
cli_temp=''
trap '[ -z "$cli_temp" ] || rm -f -- "$cli_temp"' 0
trap 'exit 130' INT
trap 'exit 143' TERM

cli_clean_profile() {
    cli_target_profile="$1"
    [ -f "$cli_target_profile" ] || return 0
    cli_temp=$(mktemp "${TMPDIR:-/tmp}/git-workflow-uninstall.XXXXXXXX")
    # Match the complete five-line installer block literally. Edited blocks,
    # other installations and unrelated user configuration remain untouched.
    if awk '
        { lines[NR] = $0 }
        END {
            removed = 0
            for (i = 1; i <= NR; i++) {
                if (lines[i] == "# Git Workflow CLI" &&
                    lines[i+1] == "case \":$PATH:\" in" &&
                    lines[i+2] == ENVIRON["CLI_MATCH_CASE"] &&
                    lines[i+3] == ENVIRON["CLI_MATCH_EXPORT"] &&
                    lines[i+4] == "esac") {
                    i += 4; removed = 1
                } else print lines[i]
            }
            if (!removed) exit 3
        }
    ' "$cli_target_profile" > "$cli_temp"; then
        if [ "$cli_dry_run" = true ]; then
            printf 'Would remove Git Workflow PATH block from %s\n' "$cli_target_profile"
        else
            # Keep the existing file's permissions and any profile symlink.
            cat "$cli_temp" > "$cli_target_profile"
            printf 'Removed Git Workflow PATH block from %s\n' "$cli_target_profile"
        fi
    else
        cli_status=$?
        [ "$cli_status" -eq 3 ] || return "$cli_status"
    fi
    rm -f -- "$cli_temp"
    cli_temp=''
}

if [ "$cli_update_path" = true ]; then
    if [ -n "$cli_profile" ]; then
        cli_clean_profile "$cli_profile"
    else
        # Clean known profiles even if the user has switched shells since installing.
        for cli_name in .bashrc .bash_profile .bash_login .profile .zshrc; do
            cli_clean_profile "${HOME}/$cli_name"
        done
    fi
else
    printf '%s\n' 'PATH cleanup skipped.'
fi
printf '%s\n' 'Installed agent skills are retained. Open a new terminal to refresh PATH.'
