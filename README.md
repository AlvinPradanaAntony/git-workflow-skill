# Git Workflow CLI

Pasang satu skill Git Workflow berisi 12 command melalui CLI yang tersedia di PATH. Jalankan dari root atau subdirektori repo tanpa menyalin installer ke setiap proyek. Git Workflow **2.13.0** memakai satu versi untuk skill, CLI, dan distribusinya. Satu file sumber `git_workflow.py` memuat CLI, payload skill, dan logika install/uninstall; executable native dibangun dari sumber yang sama.

## Distribusi release

| Distribusi | Artefak | Isi dan kebutuhan |
| --- | --- | --- |
| Windows x64 | `git-workflow-2.13.0-windows-x64.zip` | Executable mandiri, `install-cli.ps1`, dan panduan; Python tidak diperlukan |
| Linux x64 | `git-workflow-2.13.0-linux-x64.tar.gz` | Executable mandiri, `install-cli.sh`, dan panduan; dibangun di Ubuntu 22.04 |
| macOS x64 | `git-workflow-2.13.0-macos-x64.tar.gz` | Executable Intel, `install-cli.sh`, dan panduan; Apple Silicon membutuhkan Rosetta |
| Python lintas OS | `git_workflow.py` | CLI standalone dengan payload skill; membutuhkan Python 3.9+ tanpa dependensi tambahan |

Nama arsip mengikuti versi Git Workflow yang dirilis. `SHA256SUMS.txt` menyertai keempat distribusi. Binary belum ditandatangani/notarized. Git diperlukan untuk menjalankan alur kerja Git melalui agent, sedangkan pemasangan skill memakai engine Python yang sudah dibundel.

## Pasang CLI pada PATH

Unduh arsip sesuai OS dari tab Releases repo, periksa checksum yang sesuai, lalu ekstrak seluruh isinya. Helper hanya memasang executable dan mendaftarkan PATH; pemasangan skill dilakukan terpisah melalui `git-workflow install`.

Windows, jalankan PowerShell dari folder hasil ekstraksi sebagai akun pengguna biasa:

```powershell
Get-FileHash .\git-workflow-2.13.0-windows-x64.zip -Algorithm SHA256  # sebelum ekstraksi
.\install-cli.ps1
```

Executable dipasang ke `%LOCALAPPDATA%\Programs\git-workflow\bin` dan direktori tersebut ditambahkan ke user PATH. Buka terminal baru setelah pemasangan. Gunakan `-WhatIf` untuk preview, `-InstallDir PATH` untuk tujuan lain, atau `-NoPathUpdate` untuk mengelola PATH sendiri.

Linux/macOS, jalankan dari folder hasil ekstraksi:

```sh
# Linux: sha256sum git-workflow-2.13.0-linux-x64.tar.gz
# macOS: shasum -a 256 git-workflow-2.13.0-macos-x64.tar.gz
sh ./install-cli.sh
```

Executable dipasang ke `~/.local/bin`. Jika direktori belum ada di PATH, helper mendaftarkannya pada `.zshrc` untuk zsh, `.bashrc` dan profil login aktif untuk bash, atau `.profile` untuk sh/dash/ksh. Untuk shell lain seperti fish, helper memberikan petunjuk agar Anda mengatur PATH melalui konfigurasi shell tersebut. Buka terminal baru. Opsi `--bin-dir PATH`, `--profile PATH`, dan `--no-path-update` tersedia; `--profile` memilih satu file konfigurasi dengan sintaks shell POSIX. Anda juga dapat menyalin executable secara manual ke direktori yang sudah ada di PATH.

## Pakai CLI

```sh
git-workflow --help
git-workflow --version
git-workflow menu                    # menu interaktif
git-workflow commands                # pohon command CLI dan agent

cd /path/to/repo/subdirectory
git-workflow install                 # preview; mendeteksi root repo
git-workflow install --apply         # memasang skill pada repo
git-workflow status                  # periksa manifest dan hash secara read-only
git-workflow install --global --apply
git-workflow uninstall               # preview penghapusan skill proyek
git-workflow uninstall --apply
git-workflow uninstall --global --apply
```

`--project PATH` tetap tersedia untuk target eksplisit, termasuk folder proyek yang belum menjadi repo. `--replace` mempertahankan mekanisme backup dan pemeriksaan konflik engine lama. Tanpa argumen, CLI membuka menu jika stdin/stdout merupakan terminal interaktif yang mendukung tampilan; pada pipe, CI, atau terminal `dumb`, CLI menampilkan bantuan. Opsi lama seperti `git-workflow --apply` juga diterima.

### Tampilan terminal dan menu

CLI Python dan executable memakai antarmuka yang sama, tanpa dependensi runtime tambahan:

| Komponen | Penggunaan |
| --- | --- |
| ASCII banner / logo | Logo dari `assets/banner/ASCIILogo.txt` dan versi paket pada menu serta operasi terminal |
| Command tree | `commands` menampilkan pohon command CLI dan katalog 12 command agent |
| Interactive menu | Pilih install/update, uninstall, status, command tree, atau help; pilih cakupan proyek/global/path eksplisit |
| Spinner / loading | Animasi selama membaca payload/manifest dan memeriksa hash pemasangan |
| Progress bar | Jumlah file yang selesai ditulis atau dihapus saat `--apply`; tidak memakai jeda buatan |
| Status / stepper | Tahap membaca metadata, menyusun rencana, memeriksa/menerapkan perubahan, dan hasil akhir |
| Panel / box | Ringkasan rencana, preview, hasil operasi, bantuan, dan panduan kesalahan |
| Table / tree view | Tabel tujuan, rencana file, hasil pemeriksaan, serta pohon command |
| Color & icon | Warna status dan ikon dengan fallback ASCII sesuai encoding terminal |
| Help & error guidance | `--help`, contoh penggunaan, dan langkah berikutnya pada pesan error |

Menu selalu menampilkan preview lebih dahulu, lalu meminta `Apply this plan? [y/N]`. Enter atau `n` mempertahankan preview; `y` menerapkan perubahan dengan pemeriksaan konflik dan backup yang sama. Menu dapat ditutup melalui `0`, Enter pada menu utama, atau Ctrl+C. Jika Ctrl+C terjadi saat penulisan/penghapusan file, CLI mencoba memulihkan perubahan yang sudah dilakukan dan keluar dengan kode 130; backup tetap tersedia.

`status` memeriksa hanya cakupan yang dipilih, termasuk versi tercatat serta file berubah/hilang berdasarkan hash manifest. Exit code: `0` untuk pemeriksaan tanpa perubahan file atau pemasangan tidak ditemukan, `1` untuk file berubah/hilang, dan `2` untuk argumen/metadata yang tidak valid. Gunakan agent untuk memeriksa salinan skill yang benar-benar aktif.

Untuk output sederhana atau pemakaian otomatis:

```sh
git-workflow install --plain
git-workflow status --global --plain
git-workflow commands --no-color
```

`--plain` menonaktifkan dekorasi, warna, animasi, dan menu otomatis. `--no-color` atau environment `NO_COLOR` menonaktifkan warna sambil mempertahankan layout terminal. Output yang diarahkan ke file/pipe, environment CI, dan `TERM=dumb` otomatis memakai output sederhana tanpa spinner, progress, atau prompt. Command `menu` yang diminta secara eksplisit membutuhkan stdin/stdout terminal dan tidak tersedia di CI. `--version` tetap menghasilkan satu baris sederhana.

Saat menjalankan sumber di repo, banner dibaca dari `assets/banner/ASCIILogo.txt`. Salinan logo juga dibundel pada konstanta `BANNER` di `git_workflow.py` agar file Python standalone dan executable dapat berjalan tanpa folder assets. Jika logo diubah, perbarui salinan `BANNER` agar sama; preflight memeriksa kecocokannya sebelum build. Terminal sempit memakai banner ringkas, dan terminal dengan encoding terbatas memakai karakter ASCII.

CLI mengelola pemasangan skill. Command `commitmsg`, `gitpush`, dan command Git lainnya dijalankan sebagai pesan kepada agent melalui `$git-workflow commitmsg` di Codex atau `/git-workflow commitmsg` di Antigravity. Terminal `git-workflow --version` menampilkan `Git Workflow 2.13.0`, yaitu versi paket skill yang akan dipasang; `$git-workflow --version` memeriksa salinan skill yang benar-benar aktif/terpasang. Salinan lama tetap menunjukkan versi pemasangannya sampai diperbarui dengan `install --apply`.

Distribusi Python dapat diunduh dan dijalankan sendiri. Simpan `git_workflow.py` di folder mana pun, lalu jalankan dari root atau subdirektori repo tujuan:

```sh
cd /path/to/repo/subdirectory
python3 /path/to/git_workflow.py install           # preview
python3 /path/to/git_workflow.py install --apply
python3 /path/to/git_workflow.py install --global --apply
python3 /path/to/git_workflow.py uninstall --apply
```

Python dan executable memakai opsi serta deteksi repo yang sama: tujuan mengikuti folder kerja terminal, bukan lokasi skrip. `--project PATH` tersedia untuk tujuan eksplisit. File ini tidak memerlukan modul lokal lain. Installer lama telah digabung ke sumber utama; distribusi Python tetap tersedia sebagai format keempat. Panduan lengkap command agent dan perlindungan installer ada di [Panduan-Git-Workflow.md](Panduan-Git-Workflow.md).

## CI/CD

```mermaid
flowchart LR
    A[Push main / Tag / Manual] --> B[Preflight dan validasi versi/changelog]
    B --> C[Build matrix native paralel]
    C --> D[Kumpulkan dan verifikasi portable/installer/SHA-256]
    D --> E[Ekstrak release notes sesuai versi]
    E --> F{Trigger release valid?}
    F -->|Ya| G[Publish GitHub Release]
    F -->|Tidak| H[Artefak CI]
```

Workflow [build-multiplatform-release.yml](.github/workflows/build-multiplatform-release.yml) menggunakan Python dan PyInstaller sesuai codebase ini. Struktur build matrix dan catatan rilis mengikuti [workflow referensi](https://github.com/AlvinPradanaAntony/SI-Pemesanan-Kamar-Kos/blob/main/.github/workflows/build-multiplatform-release.yml); toolchain Java pada referensi diganti dengan toolchain Python.

- Push `main`: validasi, tes, build tiga OS, serta kumpulkan empat distribusi dan checksum; tidak publish.
- Push tag `v2.13.0`: versi tag harus sama dengan `VERSION` dan memiliki changelog nonkosong; release hanya dipublikasikan setelah seluruh gate berhasil.
- Manual: `version` kosong memakai metadata CLI, `publish` default false. Untuk publish, tag versi harus sudah ada dan menunjuk commit yang sama dengan ref yang dipilih. Pilih ref tag tersebut agar build sesuai release. Tag baru atau release lama tidak diganti otomatis.

Untuk release berikutnya, ubah satu konstanta `VERSION` di `git_workflow.py`, tambahkan entri changelog versi yang sama, commit perubahan, dan push tag `vVERSION`. Output CLI, manifest pemasangan, file `VERSION` skill, nama arsip, dan metadata release mengikuti konstanta tersebut. File `VERSION` skill dihasilkan saat payload dimuat sehingga nomor versi tidak perlu disunting di dalam payload terkompresi. Preflight membaca konstanta langsung dari sumber dan merekam SHA-256 `git_workflow.py`; tahap collect/publish memeriksa artefak Python terhadap hash tersebut dan sumber commit yang disetujui.

PyInstaller menghasilkan executable sesuai OS dan arsitektur tempat build dijalankan, sehingga tiap OS memakai runner native ([dokumentasi PyInstaller](https://pyinstaller.org/en/stable/operating-mode.html)). macOS memakai `macos-15-intel` untuk target x64; Linux memakai Ubuntu 22.04 agar batas kompatibilitas glibc lebih rendah dibanding runner Ubuntu terbaru. Installer di sini berupa helper PATH dan installer skill Python, bukan paket MSI/DEB/PKG.

## Pengembangan

Jalankan langkah berikut dari **root repo**, menggunakan Python yang tersedia pada komputer Anda selama memenuhi batas minimum:

| Kebutuhan | Versi Python |
| --- | --- |
| CLI dan installer Python standalone | Python 3.9+ |
| Seluruh tes, helper release, dan build | Python 3.10+; versi lebih baru mengikuti dukungan dependensi build |
| Executable native yang sudah dibangun | Python terpasang tidak diperlukan |

Batas minimum helper release berasal dari penggunaan `Path.write_text(..., newline=...)`, yang tersedia sejak Python 3.10 ([dokumentasi Python](https://github.com/python/cpython/blob/main/Doc/library/pathlib.rst)). Untuk build distribusi x64, gunakan interpreter x64. Runtime CLI dan tes unit memakai standard library; PyInstaller hanya diperlukan untuk membangun executable. Versi PyInstaller di `requirements-build.txt` menentukan interpreter yang didukung saat build, dan pip memvalidasi kompatibilitas tersebut ketika dependensi dipasang. Virtual environment disarankan agar dependensi build terpisah dari Python sistem.

Workflow CI saat ini memilih Python 3.12 agar toolchain build konsisten. Pilihan CI tersebut tidak mengharuskan pengembangan lokal memakai versi minor yang sama.

Untuk tes helper lengkap di Windows, sediakan Git Bash dan PowerShell. Smoke test build Windows membutuhkan PowerShell 7 (`pwsh`). Tes helper yang membutuhkan shell tidak tersedia akan ditandai `skipped`; periksa ringkasan tes untuk mengetahui cakupan yang benar-benar dijalankan.

### 1. Buat dan aktifkan virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux/macOS, bash atau zsh:

```sh
python3 -m venv .venv
source .venv/bin/activate
```

Perintah pembuatan environment memakai interpreter yang dirujuk `python` atau `python3` pada PATH. Di Windows, `py -3 -m venv .venv` juga dapat dipakai jika Anda menggunakan Python launcher. Jika `.venv/` sudah ada dengan versi Python yang memenuhi kebutuhan langkah yang akan dijalankan, cukup aktifkan kembali. Setelah aktivasi, perintah `python` dan `python -m pip` memakai interpreter dalam `.venv/`. Periksa sebelum melanjutkan:

```sh
python --version
python -c "import sys; print(sys.executable)"
```

Aktivasi bersifat opsional. Jika PowerShell memblokir skrip aktivasi atau Anda ingin menjalankan perintah tanpa aktivasi, gunakan interpreter environment secara langsung:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Linux/macOS memakai `.venv/bin/python` sebagai pengganti `python`. Pola yang sama berlaku untuk pip, CLI, dan helper release. Mekanisme ini mengikuti [dokumentasi venv Python](https://github.com/python/cpython/blob/main/Doc/library/venv.rst).

### 2. Pasang dependensi build

Dengan environment aktif:

```sh
python -m pip install -r requirements-build.txt
```

Langkah ini memasang versi PyInstaller yang dipatok dan dependensinya ke `.venv/`. Untuk hanya mengubah CLI atau menjalankan tes unit, langkah pemasangan dependensi build boleh dilewati.

### 3. Jalankan CLI dan tes unit

```sh
python git_workflow.py --help
python git_workflow.py --version
python -m unittest discover -s tests -v
```

Untuk menjalankan satu kelompok tes:

```sh
python -m unittest discover -s tests -p test_cli.py -v
python -m unittest discover -s tests -p test_path_installers.py -v
python -m unittest discover -s tests -p test_release.py -v
```

- `test_cli.py` menguji deteksi repo, preview, install/uninstall, idempotensi, konflik, backup, dan konsistensi versi saat memperbarui pemasangan lama pada repo contoh sementara. Tes menu mencakup navigasi, menolak/menerapkan preview, status, output plain, fallback ASCII, terminal sempit, dan rollback saat dibatalkan. Tes distribusi menyalin hanya `git_workflow.py` ke folder lain, lalu menjalankannya dalam proses Python terisolasi untuk memastikan file tersebut mandiri.
- `test_path_installers.py` menguji helper PATH dengan tujuan pemasangan dan profil shell sementara. Pemasangan PowerShell memakai `-NoPathUpdate`; user PATH serta profil shell asli tidak diubah.
- `test_release.py` menguji versi, tag, changelog, isi arsip, arsitektur binary, dan checksum memakai fixture sementara. Arsip uji tersebut bukan executable native hasil build.

Tes menggunakan direktori sementara sistem (`%TEMP%` di Windows atau lokasi temporary sistem di Linux/macOS), lalu membersihkannya saat tes selesai. Python dapat membuat `__pycache__/` di root, `scripts/`, dan `tests/`. **Tes unit tidak membuat `.venv/`, `.release/`, `build/`, `dist/`, atau `artifacts/` di repo**, tidak memasang skill ke repo pengembangan/akun asli, dan tidak mempublikasikan GitHub Release.

### 4. Validasi lokal dan buat catatan rilis

```sh
python scripts/release.py preflight --event local --publish false --output .release/metadata.json
python scripts/release.py notes --version 2.13.0 --output .release/release-notes.md
```

Ganti `2.13.0` sesuai `VERSION` di `git_workflow.py` ketika menyiapkan versi berikutnya. Preflight memeriksa file proyek, versi paket, payload skill, dan changelog; mode lokal tidak mempublikasikan release. Kedua perintah ini menghasilkan metadata dan catatan rilis dalam `.release/`.

### 5. Build, smoke test, dan packaging native

Setelah dependensi build terpasang dan preflight berhasil, pilih **satu** perintah sesuai OS host x64:

```sh
# Windows x64
python scripts/release.py build --platform windows --metadata .release/metadata.json --out-dir artifacts

# Linux x64
python scripts/release.py build --platform linux --metadata .release/metadata.json --out-dir artifacts

# macOS Intel x64
python scripts/release.py build --platform macos --metadata .release/metadata.json --out-dir artifacts
```

Helper menjalankan PyInstaller, menguji executable dari subfolder repo sementara tanpa `--project`, menguji preview/install/uninstall serta helper PATH, kemudian memverifikasi dan membuat arsip native di `artifacts/`. File kerja PyInstaller, executable sebelum packaging, dan file `.spec` dibuat di direktori sementara sistem; file kerja build itu dibersihkan setelah helper selesai. Engine uninstall menyimpan backup file uji di direktori temporary dengan awalan `git-workflow-uninstall-backup-`; backup tersebut mengikuti perilaku installer dan dapat tetap tersedia setelah smoke test.

Build lokal hanya menghasilkan distribusi **OS host** dan membutuhkan runner/interpreter x64. Contohnya, host Windows menghasilkan ZIP Windows; build Linux dan macOS dijalankan pada host masing-masing melalui matrix GitHub Actions. Validasi checksum untuk empat distribusi dilakukan pada tahap collect setelah seluruh arsip native tersedia.

Untuk debugging build secara langsung dengan PyInstaller, jalankan:

```sh
python -m PyInstaller --noconfirm --clean --onefile --console --noupx --name git-workflow git_workflow.py
```

Perintah langsung ini menghasilkan `build/`, `dist/`, dan `git-workflow.spec` di root repo. Executable berada di `dist/git-workflow.exe` pada Windows atau `dist/git-workflow` pada Linux/macOS. Perintah tersebut belum menjalankan smoke test dan packaging yang dilakukan helper `scripts/release.py build`.

### File utama dan hasil eksekusi

File utama yang dikelola dalam Git adalah `git_workflow.py`, `assets/`, `scripts/`, `tests/`, `.github/workflows/`, `requirements-build.txt`, `.gitattributes`, `.gitignore`, `README.md`, `Panduan-Git-Workflow.md`, dan `CHANGELOG.md`.

| File/folder selain sumber utama | Dibuat oleh | Keterangan |
| --- | --- | --- |
| `__pycache__/`, `*.py[cod]` | Eksekusi/import Python, termasuk tes | Cache bytecode; bisa dibuat ulang otomatis |
| `.venv/` | `python -m venv .venv` dan pip | Interpreter serta dependensi lokal; bukan hasil tes |
| `.release/` | Preflight, ekstraksi notes, dan pipeline CI | Metadata, catatan rilis, arsip native/incoming, staging assets/checksum, serta file bantu pemeriksaan |
| `build/` | Build langsung PyInstaller | Analisis, log, dan file kerja build |
| `dist/` | Build langsung PyInstaller | Executable hasil build |
| `artifacts/` | Helper build dengan `--out-dir artifacts` | Arsip distribusi native siap diambil |
| `*.spec` | PyInstaller | Pada proyek ini dihasilkan ulang; helper menyimpannya di temporary, build langsung menyimpannya di root |
| `release-assets/` | Output staging jika nama/path ini dipilih | Pola cadangan dalam `.gitignore`; workflow saat ini memakai `.release/assets/` |
| `release-notes.md` | Ekstraksi notes jika output diarahkan ke root | Workflow dan contoh lokal memakai `.release/release-notes.md` |
| `preflight.json` | Preflight jika output diberi nama tersebut | Pola cadangan dalam `.gitignore`; contoh saat ini memakai `.release/metadata.json` |

Keadaan repo yang berisi `.venv/`, `__pycache__/`, `.release/`, `build/`, `dist/`, `artifacts/`, dan `git-workflow.spec` berasal dari **beberapa langkah pengembangan/build lokal**, bukan dari tes unit saja. Semua hasil tersebut sudah dikecualikan oleh `.gitignore`; pola ignore tidak berarti setiap file/folder itu pasti ada. Pada CI, `release-assets` juga merupakan nama artifact GitHub Actions, dengan isi yang berasal dari `.release/assets/`.

Hasil eksekusi boleh dibersihkan ketika sudah tidak dibutuhkan. Jika `.venv/` dihapus, ulangi langkah pembuatan environment dan pemasangan dependensi. Jika `dist/` atau `artifacts/` dihapus, executable/arsip lokal harus dibangun ulang. Metadata `.release/` dan cache Python juga dapat dibuat ulang. Setelah mengubah README, panduan, atau helper PATH, buat ulang arsip distribusi agar konten arsip sesuai sumber yang akan diverifikasi pipeline.

Untuk keluar dari environment yang diaktifkan:

```sh
deactivate
```
