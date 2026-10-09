#!/bin/sh
# Remove the current user's native CLI; installed agent skills are retained.
set -eu

# Install the exit handler before validation so failures remain visible too.
cli_yes=false
cli_no_pause=false
cli_dry_run=false
cli_temp=''
cli_tty_state=''

cli_restore_terminal() {
    if [ -n "$cli_tty_state" ]; then
        stty "$cli_tty_state" 2>/dev/null || :
        cli_tty_state=''
    fi
}

cli_finish() {
    cli_exit_status=$?
    trap - 0
    set +e
    trap 'cli_restore_terminal; exit 130' INT
    trap 'cli_restore_terminal; exit 143' TERM
    [ -z "$cli_temp" ] || rm -f -- "$cli_temp"
    if [ "$cli_exit_status" -ne 0 ]; then
        printf '\n[ERROR] Uninstall CLI gagal (exit code %s). Lihat pesan error di atas.\n' "$cli_exit_status" >&2
    fi
    if [ "$cli_yes" != true ] && [ "$cli_no_pause" != true ] &&
        [ "$cli_dry_run" != true ] && [ -t 0 ] && [ -t 1 ]; then
        cli_tty_state=$(stty -g 2>/dev/null) || cli_tty_state=''
        if [ -n "$cli_tty_state" ] && stty -icanon -echo min 1 time 0 2>/dev/null; then
            printf '\nTekan tombol apa saja untuk selesai...'
            dd bs=1 count=1 of=/dev/null 2>/dev/null
            cli_restore_terminal
            printf '\n'
        else
            cli_restore_terminal
            printf '\nTekan Enter untuk selesai...'
            IFS= read -r cli_answer || :
        fi
    fi
    exit "$cli_exit_status"
}
trap cli_finish 0
trap 'exit 130' INT
trap 'exit 143' TERM

cli_script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
cli_bin_dir="${HOME}/.local/share/git-workflow/bin"
if [ -f "$cli_script_dir/.git-workflow-cli.files" ]; then
    cli_bin_dir="$cli_script_dir"
elif [ ! -d "$cli_bin_dir" ] && [ -f "${HOME}/.local/bin/git-workflow" ]; then
    cli_bin_dir="${HOME}/.local/bin"
fi
cli_package_files='git-workflow
install-cli.sh
uninstall-cli.sh
README.md
Panduan-Git-Workflow.md'
cli_remove_files='git-workflow'
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
        --dry-run) cli_dry_run=true; shift ;;
        --yes|-y) cli_yes=true; shift ;;
        --no-pause) cli_no_pause=true; shift ;;
        --help)
            cli_no_pause=true
            printf '%s\n' 'Usage: sh uninstall-cli.sh [--bin-dir PATH] [--profile PATH] [--no-path-update] [--dry-run] [--yes] [--no-pause]'
            exit 0 ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
    esac
done
printf '\n%s\n' '+--------------------------------------+' '|           Git Workflow CLI           |' '+--------------------------------------+' '  UNINSTALL CLI' ''
cli_tick='[OK]'
case "${LC_ALL:-${LC_CTYPE:-${LANG:-}}}" in *UTF-8*|*utf8*|*utf-8*) cli_tick=$(printf '\342\234\223') ;; esac
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
[ "$cli_bin_dir" != '/' ] || { printf '%s\n' 'The installation directory must not be a filesystem root.' >&2; exit 2; }
cli_receipt="$cli_bin_dir/.git-workflow-cli.files"
if [ -e "$cli_receipt" ] || [ -L "$cli_receipt" ]; then
    [ -f "$cli_receipt" ] && [ ! -L "$cli_receipt" ] && [ "$(cat "$cli_receipt")" = "$cli_package_files" ] || {
        printf '%s\n' 'Invalid CLI package file list. Review .git-workflow-cli.files before uninstalling.' >&2; exit 2;
    }
    cli_remove_files="$cli_package_files"
fi
for cli_name in git-workflow install-cli.sh uninstall-cli.sh README.md Panduan-Git-Workflow.md; do
    [ "$cli_remove_files" != git-workflow ] || [ "$cli_name" = git-workflow ] || continue
    cli_target="$cli_bin_dir/$cli_name"
    if [ -e "$cli_target" ] || [ -L "$cli_target" ]; then
        [ -f "$cli_target" ] && [ ! -L "$cli_target" ] || {
            printf 'Installed package member must be a regular file: %s\n' "$cli_target" >&2; exit 2;
        }
    fi
done
printf 'Tujuan : %s\n' "$cli_executable"
printf '%s\n' '[ ] Hapus file paket yang tercatat, termasuk helper dan panduan:' "$cli_remove_files"
if [ "$cli_update_path" = true ]; then
    printf '[ ] Bersihkan blok PATH milik installer (profil: %s).\n' "${cli_profile:-profil bash/zsh/POSIX yang dikenal}"
else
    printf '%s\n' '[-] Pembersihan PATH dilewati (--no-path-update).'
fi
printf '%s\n' 'Skill agent dan file lain tetap tersimpan.'
if [ "$cli_dry_run" != true ] && [ "$cli_yes" != true ]; then
    printf '\nLanjutkan uninstall CLI? [y/N] '
    if ! IFS= read -r cli_answer; then
        printf '\n%s\n' '[ERROR] Konfirmasi tidak tersedia. Gunakan --yes untuk otomasi.' >&2; exit 2
    fi
    # Accept CRLF input from Windows terminals/pipes as well as POSIX newlines.
    cli_answer=$(printf '%s' "$cli_answer" | tr -d '\015')
    case "$cli_answer" in y|Y|yes|YES|ya|YA) ;; *) printf '%s\n' 'Operasi dibatalkan. Tidak ada perubahan.'; exit 0 ;; esac
fi
if [ "$cli_dry_run" = true ]; then
    printf 'Would remove CLI (if installed): %s\n' "$cli_executable"
else
    printf '\n%s\n' '[1/2] Menghapus paket CLI...'
    # Remove the exact approved names; never recursively delete a bin directory.
    for cli_name in git-workflow install-cli.sh uninstall-cli.sh README.md Panduan-Git-Workflow.md; do
        [ "$cli_remove_files" != git-workflow ] || [ "$cli_name" = git-workflow ] || continue
        rm -f -- "$cli_bin_dir/$cli_name"
        printf '%s File paket sudah tidak ada: %s\n' "$cli_tick" "$cli_name"
    done
    printf '%s Removed CLI (if installed): %s\n' "$cli_tick" "$cli_executable"
fi

cli_escaped_dir=$(printf '%s' "$cli_bin_dir" | sed 's/["\\$`]/\\&/g')
CLI_MATCH_CASE="    *\":${cli_escaped_dir}:\"*) ;;"
CLI_MATCH_EXPORT="    *) export PATH=\"${cli_escaped_dir}:\$PATH\" ;;"
export CLI_MATCH_CASE CLI_MATCH_EXPORT

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
            printf '%s Removed Git Workflow PATH block from %s\n' "$cli_tick" "$cli_target_profile"
        fi
    else
        cli_status=$?
        [ "$cli_status" -eq 3 ] || return "$cli_status"
        printf '[-] Tidak ada blok PATH yang cocok di %s; profil dipertahankan.\n' "$cli_target_profile"
    fi
    rm -f -- "$cli_temp"
    cli_temp=''
}

printf '%s\n' '[2/2] Memeriksa blok konfigurasi PATH...'
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
    printf '%s\n' '[-] PATH cleanup skipped.'
fi
if [ "$cli_dry_run" = true ]; then
    printf '%s\n' 'Preview selesai; tidak ada perubahan.'; exit 0
fi
rm -f -- "$cli_receipt"
# rmdir removes empty directories only. Shared/custom directories with other
# files are retained, and parent cleanup is limited to the dedicated default.
if [ -d "$cli_bin_dir" ] && [ -z "$(ls -A -- "$cli_bin_dir")" ]; then
    case "$(pwd)" in "$cli_bin_dir") cd -- "$(dirname -- "$cli_bin_dir")" ;; esac
    rmdir -- "$cli_bin_dir"
    printf '%s Folder pemasangan kosong dibersihkan.\n' "$cli_tick"
    if [ "$cli_bin_dir" = "${HOME}/.local/share/git-workflow/bin" ]; then
        rmdir -- "${HOME}/.local/share/git-workflow" 2>/dev/null || :
    fi
elif [ -d "$cli_bin_dir" ]; then
    printf '%s\n' '[-] Folder dipertahankan karena masih berisi file lain.'
fi
printf '\n%s Uninstall CLI sukses.\n' "$cli_tick"
printf '%s\n' 'Installed agent skills are retained. Open a new terminal to refresh PATH.'
