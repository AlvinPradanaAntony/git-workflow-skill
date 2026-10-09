#!/bin/sh
# Run from an extracted Linux/macOS release archive, as the current user.
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
        printf '\n[ERROR] Install CLI gagal (exit code %s). Lihat pesan error di atas.\n' "$cli_exit_status" >&2
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
if [ -f "$cli_script_dir/.git-workflow-cli.files" ]; then cli_bin_dir="$cli_script_dir"; fi
cli_package_files='git-workflow
install-cli.sh
uninstall-cli.sh
README.md
Panduan-Git-Workflow.md'
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
        --yes|-y) cli_yes=true; shift ;;
        --no-pause) cli_no_pause=true; shift ;;
        --dry-run) cli_dry_run=true; shift ;;
        --help)
            cli_no_pause=true
            printf '%s\n' 'Usage: sh install-cli.sh [--bin-dir PATH] [--profile PATH] [--no-path-update] [--dry-run] [--yes] [--no-pause]'
            exit 0 ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
    esac
done
printf '\n%s\n' '+--------------------------------------+' '|           Git Workflow CLI           |' '+--------------------------------------+' '  INSTALL CLI' ''
cli_tick='[OK]'
case "${LC_ALL:-${LC_CTYPE:-${LANG:-}}}" in *UTF-8*|*utf8*|*utf-8*) cli_tick=$(printf '\342\234\223') ;; esac
case "$cli_bin_dir" in
    *:*|*'
'*) printf '%s\n' 'The installation directory cannot contain a colon or newline.' >&2; exit 2 ;;
esac
cli_source="$cli_script_dir/git-workflow"
[ ! -e "$cli_script_dir/.git" ] || { printf '%s\n' 'Run the installer from an extracted release archive, not a repository root.' >&2; exit 2; }
[ -f "$cli_source" ] || { printf '%s\n' 'git-workflow must be beside this script. Extract the complete release archive first.' >&2; exit 2; }
case "$cli_bin_dir" in /*) ;; *) cli_bin_dir="$(pwd)/$cli_bin_dir" ;; esac
if [ -d "$cli_bin_dir" ]; then cli_bin_dir=$(CDPATH='' cd -- "$cli_bin_dir" && pwd); fi
[ "$cli_bin_dir" != '/' ] || { printf '%s\n' 'The installation directory must not be a filesystem root.' >&2; exit 2; }
cli_receipt="$cli_bin_dir/.git-workflow-cli.files"
cli_owns_package=false
if [ -e "$cli_receipt" ] || [ -L "$cli_receipt" ]; then
    [ -f "$cli_receipt" ] && [ ! -L "$cli_receipt" ] && [ "$(cat "$cli_receipt")" = "$cli_package_files" ] || {
        printf '%s\n' 'Invalid CLI package file list. Review .git-workflow-cli.files before installing.' >&2; exit 2;
    }
    cli_owns_package=true
fi
for cli_name in git-workflow install-cli.sh uninstall-cli.sh README.md Panduan-Git-Workflow.md; do
    [ -f "$cli_script_dir/$cli_name" ] && [ ! -L "$cli_script_dir/$cli_name" ] || {
        printf 'Missing or non-regular package member: %s. Extract the complete release archive first.\n' "$cli_name" >&2; exit 2;
    }
    cli_target="$cli_bin_dir/$cli_name"
    if [ -e "$cli_target" ] || [ -L "$cli_target" ]; then
        [ -f "$cli_target" ] && [ ! -L "$cli_target" ] || {
            printf 'Destination package member must be a regular file: %s\n' "$cli_target" >&2; exit 2;
        }
        if [ "$cli_script_dir" != "$cli_bin_dir" ] && [ "$cli_owns_package" != true ] && [ "$cli_name" != git-workflow ]; then
            printf 'An unowned file already exists at %s. Choose another --bin-dir.\n' "$cli_target" >&2; exit 2
        fi
    fi
done
printf 'Sumber : %s\nTujuan : %s\n' "$cli_script_dir" "$cli_bin_dir"
printf '%s\n' '[ ] Pindahkan seluruh isi paket release (cut):' "$cli_package_files"
if [ "$cli_update_path" = true ]; then
    printf '[ ] Daftarkan PATH bila diperlukan (profil: %s).\n' "${cli_profile:-otomatis sesuai shell}"
else
    printf '%s\n' '[-] Pendaftaran PATH dilewati (--no-path-update).'
fi
printf '%s\n' 'Skill agent dipasang terpisah melalui git-workflow install.'
if [ "$cli_dry_run" = true ]; then
    printf '%s\n' 'Preview selesai; tidak ada perubahan.'; exit 0
fi
if [ "$cli_yes" != true ]; then
    printf '\nLanjutkan install CLI? [y/N] '
    if ! IFS= read -r cli_answer; then
        printf '\n%s\n' '[ERROR] Konfirmasi tidak tersedia. Gunakan --yes untuk otomasi.' >&2; exit 2
    fi
    # Accept CRLF input from Windows terminals/pipes as well as POSIX newlines.
    cli_answer=$(printf '%s' "$cli_answer" | tr -d '\015')
    case "$cli_answer" in y|Y|yes|YES|ya|YA) ;; *) printf '%s\n' 'Operasi dibatalkan. Tidak ada perubahan.'; exit 0 ;; esac
fi
printf '\n%s\n' '[1/2] Memindahkan paket release...'
mkdir -p -- "$cli_bin_dir"
cli_bin_dir=$(CDPATH='' cd -- "$cli_bin_dir" && pwd)
[ "$cli_bin_dir" != '/' ] || { printf '%s\n' 'The installation directory must not be a filesystem root.' >&2; exit 2; }
# Record approved names before moving so a partial move remains removable.
printf '%s\n' "$cli_package_files" > "$cli_bin_dir/.git-workflow-cli.files"
for cli_name in git-workflow install-cli.sh uninstall-cli.sh README.md Panduan-Git-Workflow.md; do
    if [ "$cli_script_dir" != "$cli_bin_dir" ]; then
        mv -f -- "$cli_script_dir/$cli_name" "$cli_bin_dir/$cli_name"
    fi
    printf '%s Paket terpasang: %s\n' "$cli_tick" "$cli_name"
done
chmod 755 "$cli_bin_dir/git-workflow" "$cli_bin_dir/install-cli.sh" "$cli_bin_dir/uninstall-cli.sh"
printf '%s Installed CLI: %s/git-workflow\n' "$cli_tick" "$cli_bin_dir"

cli_register_profile() {
    cli_target_profile="$1"
    if [ ! -f "$cli_target_profile" ] || ! grep -Fqx -- "$cli_export_line" "$cli_target_profile"; then
        printf '\n# Git Workflow CLI\ncase ":$PATH:" in\n    *":%s:"*) ;;\n%s\nesac\n' \
            "$cli_escaped_dir" "$cli_export_line" >> "$cli_target_profile"
    fi
    printf '%s PATH registered in %s\n' "$cli_tick" "$cli_target_profile"
}

printf '%s\n' '[2/2] Memeriksa konfigurasi PATH...'
if [ "$cli_update_path" = true ]; then
    case ":${PATH}:" in
        *":${cli_bin_dir}:"*) printf '%s PATH sudah tersedia.\n' "$cli_tick" ;;
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
printf '\n%s Install CLI sukses.\n' "$cli_tick"
printf 'Helper uninstall tersedia di: %s/uninstall-cli.sh\n' "$cli_bin_dir"
if [ "$cli_update_path" = true ]; then
    printf '%s\n' 'Open a new terminal, then run: git-workflow --version'
else
    printf '%s\n' '[-] PATH registration skipped. Add the installation directory to PATH to use git-workflow by name.'
fi
