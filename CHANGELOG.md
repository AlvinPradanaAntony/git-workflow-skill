# Changelog

Perubahan skill, CLI, dan distribusi Git Workflow dengan satu versi paket.

## [2.15.0] - 2026-10-09

### Added

- Banner dan daftar aksi pada helper install/uninstall shell serta PowerShell, konfirmasi default tidak, status centang per langkah, pesan sukses, dan jeda akhir pada terminal interaktif tanpa redraw layar.
- Opsi `--yes`/`-Yes` untuk helper pada CI, serta `--dry-run` pada installer shell; input konfirmasi yang tidak tersedia menghentikan perubahan.
- Jeda tekan tombol apa saja pada install/uninstall Windows, Linux, dan macOS setelah sukses, pembatalan, atau error; fallback Enter untuk host terbatas, opsi `-NoPause`/`--no-pause`, dan exit code kegagalan tetap dipertahankan.

### Changed

- Format release memakai judul `🎉 Git Workflow vVERSI` dan heading notes `📋 Apa yang Baru di vVERSI?`, mengikuti gaya TonzToon; helper notes yang dibundel memakai heading yang sama.
- Publish melalui workflow CI yang sudah tersedia langsung memicu tag/manual publish tanpa mengulang validasi versi/changelog, build, signing, artefak/checksum dan notes secara lokal; status run dilaporkan tanpa menunggu build secara default, dengan pemantauan selesai bila diminta. Jalur direct dan operasi destruktif mempertahankan pemeriksaan yang relevan.
- Semua 12 command skill memakai pemeriksaan sesuai aksi, eksekusi langsung ketika cakupan jelas, pemakaian ulang bukti yang belum berubah, serta diagnosis error dan saran retry tanpa validasi tes/build rutin. Hook, aturan repo, backup dan gate publikasi yang relevan tetap berlaku.
- Helper install memindahkan seluruh lima file arsip native ke tujuan, termasuk helper dan panduan. Uninstall memakai catatan kepemilikan file untuk menghapus seluruh paket serta folder kosong tanpa menghapus file lain atau skill agent.
- Tujuan default Linux/macOS menjadi `~/.local/share/git-workflow/bin` agar seluruh paket berada di folder khusus. Helper terpasang mengenali tujuannya sendiri; instalasi lama tetap dapat dibersihkan sebagai executable saja.

## [2.14.0] - 2026-10-08

### Added

- Helper `uninstall-cli.ps1` dan `uninstall-cli.sh` dibundel pada arsip native, dengan preview, tujuan khusus, dan pembersihan PATH milik installer tanpa menghapus skill agent atau tool lain.
- Installer Windows mencatat kepemilikan entri PATH agar uninstall mempertahankan entri yang sudah ada sebelum pemasangan.
- Template workflow build/release dan referensi enam tahap dibundel pada payload untuk `gitrelease init`, dengan pilihan target/arsitektur dan portable/installer berdasarkan codebase.
- Helper notes skill mendukung judul nama proyek/versi dan output file dengan perlindungan agar changelog sumber tidak ditimpa.
- Setup interaktif untuk memilih satu/beberapa agent dan cakupan repo, direktori proyek, atau global pengguna.
- Command `agents` untuk menampilkan 20 target, ID, lokasi discovery repo/global, dan override environment yang aktif.
- Opsi `--agent` pada install, update, status dan uninstall, dengan ID berulang, daftar dipisahkan koma, alias nama dan pilihan `all`.
- Pemetaan skill untuk Claude Code, Codex, Antigravity IDE/2.0 dan CLI, OpenCode, Cursor, Cline, Roo Code, Amp, Gemini CLI, Hermes, GitHub Copilot, Kimi Code, Kiro, Qoder, Pi, Kilo Code, TRAE, Zencoder/Zen CLI dan Oh My Pi.
- Dukungan user config roots `CLAUDE_CONFIG_DIR`, `XDG_CONFIG_HOME` (OpenCode/Amp), `HERMES_HOME`, `PI_CODING_AGENT_DIR` dan profile Oh My Pi melalui `OMP_PROFILE`/`PI_PROFILE`.

### Changed

- Init menghasilkan versioning proyek, changelog, workflow dan helper aktual; trigger push tag versi/manual serta gate artefak/SHA-256 konsisten dengan repo Git Workflow.
- Workflow repo dan template init memakai trigger otomatis hanya tag `v*.*.*`; push main/branch lain tidak menjalankan pipeline release. Manual tetap tersedia dengan publish default false; preflight menolak event push branch.
- Format notes default init mengambil satu versi changelog dengan judul proyek/versi; layout Download/riwayat tetap tersedia sebagai pilihan eksplisit.
- Manifest schema 2 mencatat kepemilikan file serta versi per agent. Install/update mempertahankan agent lain; uninstall sebagian mempertahankan file bersama sampai pemilik terakhir dihapus.
- Manifest lama dimigrasikan dengan mempertahankan target Codex/Antigravity dan perlindungan terhadap file yang diubah pengguna.
- Instalasi baru tanpa selector memakai Codex; instalasi yang sudah ada tanpa selector memakai seluruh target tercatat. Setup menyediakan pemilihan eksplisit.
- Instruksi skill dan pemeriksaan versi aktif memakai direktori skill yang dipilih host, termasuk lokasi native dan konfigurasi pengguna di luar home.
- README memuat pemetaan bersumber dokumentasi resmi, batas discovery lintas agent, serta langkah verifikasi dan trust per host.

### Notes

- Installer memasang skill pada filesystem lokal. Lokasi user tidak otomatis tersedia di cloud agent/remote host; lakukan pemasangan pada lingkungan tempat agent berjalan.
- Perilaku discovery bergantung pada versi agent, konfigurasi skill dan trust workspace. Pengujian installer tidak menggantikan pengujian sesi nyata pada seluruh aplikasi agent.

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
