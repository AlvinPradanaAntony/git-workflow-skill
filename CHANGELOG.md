# Changelog

Perubahan skill, CLI, dan distribusi Git Workflow dengan satu versi paket.

## [2.13.0] - 2026-10-08

### Added

- CLI `git-workflow` dengan bantuan terminal, informasi versi paket skill, serta perintah install dan uninstall.
- Deteksi root repo dari direktori kerja, termasuk subdirektori dan penanda Git worktree.
- Build executable PyInstaller pada runner Windows x64, Linux x64 dan macOS x64.
- Helper pemasangan executable ke PATH akun pengguna pada tiap distribusi native.
- Pipeline preflight, validasi versi/changelog, build paralel, verifikasi artefak, checksum SHA-256, ekstraksi catatan rilis, dan publikasi GitHub Release.
- Publikasi dari tag valid atau manual dengan pilihan publish eksplisit dan tag yang menunjuk commit yang dibangun.
- Distribusi Python lintas OS berupa `git_workflow.py` standalone, dengan opsi dan deteksi repo yang sama dengan executable.
- Antarmuka terminal dengan ASCII banner, command tree, menu interaktif, spinner, progress file, stepper, panel, tabel, warna/ikon, dan panduan kesalahan.
- Banner memakai logo `assets/banner/ASCIILogo.txt`, dengan salinan yang dibundel untuk Python standalone/executable serta fallback terminal sempit dan encoding ASCII.
- Command `status` untuk pemeriksaan read-only manifest pemasangan dan file berubah/hilang; `commands` untuk katalog CLI/agent, serta `menu` untuk navigasi interaktif.
- Opsi `--plain`, `--no-color`, dukungan `NO_COLOR`, serta fallback output sederhana pada pipe/CI/terminal terbatas.

### Changed

- Payload dan logika install/uninstall dari installer lama digabung ke `git_workflow.py`. Executable native dan artefak Python memakai sumber yang sama; file installer terpisah dihapus.
- Satu konstanta `VERSION` menjadi sumber versi skill, CLI, manifest, arsip, dan metadata release. File versi skill dihasilkan dari konstanta saat payload dimuat.
- Preflight dan verifikasi release membaca versi paket serta checksum artefak Python dari sumber utama.
- Menu tanpa argumen tersedia pada terminal interaktif. Penerapan perubahan melalui menu tetap didahului preview dan pilihan pengguna; Ctrl+C saat perubahan file memicu rollback.

### Notes

- Skill dan CLI memakai versi 2.13.0 dengan alur kerja serta perlindungan installer yang sama. Release berisi tiga distribusi native dan satu CLI Python.
- Push main dan build manual biasa hanya menghasilkan artefak CI. CLI tetap memakai preview sampai opsi `--apply` diberikan.

## [2.12.4] - 2026-10-03

### Added

- Pemeriksaan versi/pemasangan melalui command agent `--version`.

### Changed

- Alur `gitrelease` mendukung proyek non-web, mengikuti codebase dan distribusi proyek.

### Notes

- Entri ini mencatat perubahan paket 2.12.4 yang sudah dijelaskan pada panduan installer sebelumnya.
