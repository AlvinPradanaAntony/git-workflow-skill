# Git Workflow: satu skill untuk 12 command Git, help dan pemeriksaan versi

Versi Git Workflow **2.13.0**, diperbarui pada 8 Oktober 2026. Skill, CLI, dan distribusi memakai satu konstanta `VERSION` pada sumber utama. Sumber tunggal `git_workflow.py` memuat CLI, payload skill, serta logika install/uninstall dan didistribusikan sebagai executable native maupun skrip Python standalone. Paket ini mencakup pemeriksaan pemasangan `--version` melalui agent dan logic `gitrelease` untuk semua proyek non-web. Skill **Git Workflow** memuat dua belas alur kerja Git sebagai referensi perintah. Mode proyek memasang **satu** folder skill `.agents/skills/git-workflow/` di repo serta rule modular `.agents/rules/git-workflow.md`. Mode global memasang satu salinan skill pada lokasi masing-masing aplikasi untuk akun pengguna saat ini. Jika daftar skill belum diperbarui, buka ulang sesi agent. Penemuan otomatis tidak berarti perintah langsung dijalankan.

## Pemasangan melalui CLI di PATH

Unduh distribusi Windows x64, Linux x64, atau macOS x64 dari GitHub Release, ekstrak, lalu jalankan helper `install-cli.ps1` (Windows) atau `sh install-cli.sh` (Linux/macOS) dari folder hasil ekstraksi. Helper memasang executable ke direktori pengguna dan mendaftarkan PATH. Python tidak diperlukan untuk executable native. Cara lengkap, checksum, batas platform dan pipeline release ada di [README.md](README.md).

Dari root atau subdirektori repo, CLI memilih root Git berdasarkan folder kerja terminal:

```sh
git-workflow --help
git-workflow --version
git-workflow menu
git-workflow commands
git-workflow install
git-workflow install --apply
git-workflow install --global --apply
git-workflow uninstall --apply
git-workflow status
```

Tanpa `--apply`, CLI hanya menampilkan rencana. `--project PATH` tetap tersedia untuk tujuan eksplisit. `--replace` memakai pemeriksaan konflik dan backup installer yang sama. Command Git seperti `commitmsg` tetap merupakan pesan kepada agent, bukan subcommand executable. `git_workflow.py` disertakan sebagai distribusi keempat dan dapat dijalankan sendiri sebagaimana dijelaskan berikut.

Menjalankan `git-workflow` tanpa argumen dari terminal interaktif membuka menu dengan banner, tabel pilihan, dan command tree. Pilih install/update atau uninstall, tentukan cakupan, lalu tinjau preview sebelum menjawab `y` pada pertanyaan penerapan. `status` memeriksa hash manifest tanpa mengubah pemasangan. Spinner, progress bar file, stepper, panel hasil, warna, dan ikon tampil pada terminal yang mendukungnya; encoding terbatas memakai ikon ASCII. Gunakan `--plain` untuk output sederhana, atau `--no-color`/environment `NO_COLOR` untuk menghilangkan warna. Pipe, CI, dan terminal `dumb` otomatis menggunakan output sederhana tanpa prompt. Petunjuk lengkap dan exit code ada di [README.md](README.md#tampilan-terminal-dan-menu).

## Pemasangan lokal melalui CLI Python standalone

Unduh `git_workflow.py` dan simpan di folder mana pun. Perlu Python 3.9+ tanpa dependensi Python tambahan, serta Git untuk memakai alur kerja. Jalankan dari root atau subdirektori repo tujuan; CLI mendeteksi root Git dari **folder kerja terminal**. Misalnya, jika skrip disimpan di `D:\Tools`:

```powershell
cd "D:\Projects\nama-project"
py "D:\Tools\git_workflow.py" install
py "D:\Tools\git_workflow.py" install --apply
```

Untuk memilih tujuan eksplisit, termasuk folder yang belum menjadi repo Git, gunakan `--project`:

```powershell
py "D:\Tools\git_workflow.py" install --project "D:\Projects\nama-project" --apply
```

Jika folder kerja berada di luar repo Git, pilih `--project` atau `--global`. Tanpa argumen, CLI membuka menu pada terminal interaktif yang mendukungnya dan menampilkan bantuan pada output sederhana; `install` tanpa `--apply` hanya menampilkan rencana. macOS/Linux: ganti `py` dengan `python3` dan sesuaikan path. Installer memasang satu skill dan tidak membuat shortcut `.agents/workflows/`. Gunakan `$git-workflow commitmsg` di Codex atau `/git-workflow commitmsg` di Antigravity.

Katalog dua belas command beserta parameternya tersedia melalui `$git-workflow help` di Codex, `/git-workflow help` di Antigravity, atau `help` setelah memilih skill Git Workflow di ChatGPT. Parameter `--lang`, `--format`, dan `--to` digunakan dalam **pesan kepada agent**. CLI terminal menyediakan `--help` untuk opsi pemasangan dan `--version` untuk versi paket skill. Pemeriksaan versi skill aktif melalui agent dijelaskan pada bagian berikutnya.

## Pemasangan global untuk akun pengguna

Simpan skrip di folder mana pun, lalu jalankan dengan `--global`. Tanpa `--apply`, skrip hanya menampilkan rencana. Jalankan sebagai akun pengguna biasa agar terpasang pada akun yang Anda pakai menjalankan Codex dan Antigravity:

```powershell
py "D:\Tools\git_workflow.py" install --global
py "D:\Tools\git_workflow.py" install --global --apply
```

Mode ini memasang paket skill yang sama pada tiga lokasi resmi:

| Aplikasi | Lokasi global |
| --- | --- |
| Codex CLI/IDE | `~/.agents/skills/git-workflow/` |
| Antigravity IDE/2.0 | `~/.gemini/config/skills/git-workflow/` |
| Antigravity CLI | `~/.gemini/antigravity-cli/skills/git-workflow/` |

`~` berarti folder pengguna saat ini (`%USERPROFILE%` di Windows). Pemasangan global tidak menyunting `AGENTS.md` atau file repo apa pun. `--global` tidak boleh digabung dengan `--project`. Jika ada file skill berbeda di lokasi tujuan, installer berhenti; setelah ditinjau, `--replace --apply` membuat backup sebelum menggantinya. Mode global mengatur akun komputer tempat skrip dijalankan, bukan instalasi skill di ChatGPT browser/cloud.

Jika proyek pernah dipasang dengan paket versi 1, 2.0, 2.3, atau 2.4, installer membaca manifest yang sudah ada, memindahkan alur ke satu skill, dan menghapus **hanya file lama yang tercatat milik paket**. File `.agents/git-workflow.rules.md` versi lama dipindahkan ke `.agents/rules/git-workflow.md` dengan frontmatter `trigger: model_decision`. Shortcut `.agents/workflows/` yang tercatat di manifest versi lama juga dibersihkan. Rule lain di `.agents/rules/` tetap utuh. Perubahan manual yang tidak cocok dengan manifest menghentikan migrasi. Setelah meninjau perbedaannya, `--replace --apply` menyimpan backup file lama sebelum menggantinya. Aturan di luar blok Git Workflow pada `AGENTS.md` tetap utuh. Installer tidak menjalankan commit, push, atau unduhan dependensi.

## Menghapus pemasangan

Gunakan command `uninstall` untuk melihat rencana penghapusan, lalu tambahkan `--apply` untuk menghapus. Jalankan dari root atau subdirektori repo tujuan:

```powershell
py "D:\Tools\git_workflow.py" uninstall
py "D:\Tools\git_workflow.py" uninstall --apply
```

Untuk pemasangan global milik akun pengguna saat ini:

```powershell
py "D:\Tools\git_workflow.py" uninstall --global
py "D:\Tools\git_workflow.py" uninstall --global --apply
```

Dari folder lain, gunakan `uninstall --project "D:\Projects\nama-project" --apply` untuk pemasangan proyek. Alias lama `--uninstall` tetap diterima. Skrip membaca manifest dan hanya menghapus file paket yang tercatat, serta blok Git Workflow dalam `AGENTS.md`; instruksi lain tetap ada. File yang diubah secara manual menghentikan proses. Setelah meninjau perbedaannya, `uninstall --replace --apply` membuat backup dan menghapus file paket yang dimodifikasi. Setiap penghapusan yang diterapkan menyimpan backup file sebelumnya di folder sementara, dan pemasangan global tidak mengubah repo. Jika manifest tidak ada, skrip tidak menghapus file apa pun.

## Cara memanggil

| Tempat | Contoh |
| --- | --- |
| ChatGPT browser/cloud | Pilih skill **Git Workflow**, lalu tulis `commitmsg --lang both` atau `/commitmsg --lang both` sebagai pesan |
| Codex CLI/IDE | `$git-workflow commitmsg --lang both` |
| Antigravity | `/git-workflow commitmsg --lang both` |

Codex membaca `AGENTS.md` di root proyek; blok Git Workflow di dalamnya mengarahkan tugas Git ke `.agents/rules/git-workflow.md` dan skill `.agents/skills/git-workflow/SKILL.md`. Codex tidak mengindeks isi `.agents/rules/` sebagai instruksi proyek secara otomatis. Antigravity mengindeks rule tersebut melalui `trigger: model_decision`. Slash command pendek dalam ChatGPT/Codex hanya berfungsi sebagai teks jika antarmuka meneruskannya ke agent; skill tidak mendaftarkan custom slash command bawaan Codex. Skill di proyek berlaku bagi proyek tersebut; pemasangan di ChatGPT browser/cloud terpisah. Jika daftar Skills masih menampilkan versi lama sesaat setelah pembaruan, refresh halaman Skills.

## Memeriksa pemasangan dan versi skill

Kirim perintah berikut kepada agent setelah skill Git Workflow dipilih atau tersedia:

```text
git-workflow --version
```

Gunakan `$git-workflow --version` di Codex atau `/git-workflow --version` di Antigravity. Di ChatGPT, pilih Git Workflow lalu kirim `--version`. Ini utilitas tingkat atas di samping help; nomor 1–12 command Git tetap sama. Jangan gabungkan dengan command Git atau parameter lain. Pemeriksaan ini merupakan pesan kepada agent. Terminal `git-workflow --version` atau `py "D:\Tools\git_workflow.py" --version` menampilkan **versi paket skill** sebagai `Git Workflow 2.13.0`, sedangkan versi skill yang aktif/terpasang diperiksa oleh agent. File `VERSION` skill dan manifest mengikuti konstanta paket saat pemasangan; salinan lama perlu diperbarui dengan `install --apply`.

Agent memeriksa skill yang benar-benar dipilih host, lalu pemasangan proyek dan global Codex/Antigravity yang dapat diakses. Hasil memuat versi konten dari file `VERSION`, versi tercatat di manifest, status pemasangan, lokasi/cakupan, dan salinan mana yang aktif. Pemeriksaan tidak menjalankan Git, memasang dependensi, memperbarui skill, mengubah file, atau mengakses jaringan.

| Keadaan | Hasil pemeriksaan |
| --- | --- |
| Skill aktif versi 2.13.0 | Tampilkan **2.13.0** dari file VERSION pada salinan yang dipilih host. |
| Salinan proyek/global berbeda versi | Tampilkan setiap versi secara terpisah; salinan terbaru tidak otomatis dianggap aktif. |
| Berkas paket berubah/hilang atau versi manifest berbeda | Tampilkan status perubahan/ketidaksesuaian dari pemeriksaan hash dan metadata; tidak diperbaiki otomatis. |
| Pemasangan lama belum memiliki VERSION | Tampilkan versi manifest sebagai **versi tercatat**; versi konten belum terverifikasi. Jangan menebak versi terbaru dari installer. |
| Skill aktif ChatGPT tanpa manifest installer lokal | Versi dibaca dari salinan aktif; status tersedia tanpa verifikasi manifest, bukan otomatis rusak. |
| Pemasangan tidak ditemukan | Nyatakan belum terpasang pada lokasi yang diperiksa; manifest lama saja tidak membuktikan skill masih ada. |
| Host tidak memperlihatkan lokasi aktif atau filesystem/Python tidak tersedia | Nyatakan keterbatasan dan versi/salinan aktif yang belum dapat diverifikasi. |

Versi skill berbeda dari versi aplikasi/proyek yang diproses oleh `gitrelease`. Pesan agent `$git-workflow --version` memeriksa pemasangan skill, sedangkan `gitrelease prepare --version 1.2.0` memilih versi rilis proyek. `help --cmd --version` hanya menjelaskan utilitas ini tanpa menjalankan pemeriksaan.

Untuk memperbarui pemasangan lokal/global lama, unduh installer terbaru lalu jalankan kembali perintah pemasangan pada cakupan yang sama, dengan `--apply`. Installer menambahkan metadata VERSION dan helper pemeriksaan ke salinan yang dikelolanya. File yang diubah manual tetap mengikuti aturan konflik/backup installer. Mengunduh installer baru saja tidak mengubah skill yang sudah terpasang.

## Dua belas command Git

| Command | Efek |
| --- | --- |
| `--version` | Periksa versi skill terpasang, manifest dan salinan aktif; read-only; utilitas tanpa nomor |
| `help` | Katalog dua belas command dan parameternya; read-only |
| `gitstatus` | Ringkasan repository; read-only |
| `commitpln` | Rencana pembagian commit dan draft pesan; read-only; alias teks `commitplan` |
| `commitmsg` | Menyusun pesan lalu membuat commit lokal; tidak push |
| `branchname` | Usul nama branch; read-only |
| `prdesc` | Draft PR; tidak membuat PR |
| `gitundo` | Mengembalikan commit menjadi staged atau changes |
| `gitreset` | Reset lokal dengan mode soft, mixed atau hard yang eksplisit |
| `gitmergecancel` | Keep hasil merge sebagai perubahan, atau abort merge |
| `gitamend` | Amend staged changes tanpa mengubah pesan; lokal |
| `gitpushamend` | Amend no-edit lalu targeted push; lease terikat SHA remote jika perlu rewrite |
| `gitpush` | Push biasa ke target yang terverifikasi |
| `gitrelease` | Versioning dan GitHub Release untuk semua proyek selain website/aplikasi web berbasis browser; aksi init/prepare/publish/delete; tanpa aksi menampilkan bantuan |

Contoh umum:

```text
$git-workflow help
$git-workflow commitpln --lang both
$git-workflow commitmsg --format standard --lang both
$git-workflow gitundo --to changes
$git-workflow gitreset --soft --to HEAD~1
$git-workflow gitmergecancel --keep --to changes
$git-workflow gitpushamend --remote origin --branch feature/login
```

Ganti awalan `$git-workflow` sesuai tempat penggunaan pada tabel di atas. Default `gitundo` ialah satu commit ke staged. `gitreset` membutuhkan mode dan target eksplisit. `gitmergecancel` membutuhkan keep atau abort. Perubahan yang belum selesai atau konflik perlu diperiksa sebelum tindakan.

## Tampilan bantuan

`help` tanpa opsi menampilkan tabel ringkas dengan kolom **No.**, **Command**, **Deskripsi**, dan **Opsi / nilai**. Deskripsi berdiri sendiri; opsi dan nilai yang tersedia berada pada kolom tersendiri. Parameter pesan bersama untuk commitpln/commitmsg dijelaskan sekali setelah tabel.

`help --detailed` menampilkan penjelasan lengkap per command dengan numbering, **Deskripsi**, **Aksi/mode** jika tersedia, **Parameter** beserta nilai/default dan fungsi singkat, serta contoh. Bentuk `help detailed` juga diterima.

`help --cmd` **tanpa nilai** menampilkan semua nama command Git sebagai daftar bernomor 1–12 saja, tanpa deskripsi atau parameter. Ini valid dan tidak dianggap argumen yang hilang. Jika digabung dengan --detailed tanpa nilai --cmd, daftar nama bernomor tetap didahulukan.

`help --cmd --version` menampilkan detail pemeriksaan versi saja, tanpa memeriksa pemasangan. Help dan --version tidak mengambil nomor Git.

`help --cmd NOMOR_ATAU_NAMA` langsung menampilkan **detail satu command**, tanpa harus menambahkan detailed. Kombinasi dengan --detailed tetap hanya menampilkan pilihan tersebut. Nomor command stabil:

| No. | Command |
| --- | --- |
| 1 | gitstatus |
| 2 | commitpln |
| 3 | commitmsg |
| 4 | branchname |
| 5 | prdesc |
| 6 | gitundo |
| 7 | gitreset |
| 8 | gitmergecancel |
| 9 | gitamend |
| 10 | gitpushamend |
| 11 | gitpush |
| 12 | gitrelease |

Help sendiri tidak mengambil nomor pada daftar dua belas command; gunakan --cmd help jika ingin rincian bantuan. Nama command tidak peka huruf besar/kecil; satu awalan slash dan alias commitplan diterima. Nilai --cmd harus nomor 1–12 atau nama command yang tersedia. Target yang diberikan tetapi tidak dikenal, nomor di luar rentang, selector berulang atau opsi tidak didukung menghasilkan penjelasan kesalahan dan contoh pemakaian tanpa memeriksa repo.

Contoh di Antigravity:

```text
/git-workflow help
/git-workflow help --detailed
/git-workflow help detailed
/git-workflow help --cmd
/git-workflow help --cmd 2
/git-workflow help --cmd commitpln
/git-workflow help --cmd gitrelease --detailed
/git-workflow help --cmd --version
```

Di Codex, ganti awalan /git-workflow dengan $git-workflow. --cmd 2 dan --cmd commitpln menampilkan detail yang sama, termasuk parameter pesan bersama. Parameter help digunakan dalam pesan ke agent, bukan pada skrip installer. Help hanya membaca dokumentasi; tidak menjalankan command yang dipilih, memeriksa repo atau menjalankan Git/installer.

## Format pesan commit

`--format short|standard|detailed` dan `--lang en|id|both` (default en). Untuk `commitmsg` tanpa `--format`, jika tepat satu file berubah di repository maka pilih **short**; jika lebih dari satu maka pilih **standard**. Hitung path unik dari staged, unstaged, dan file baru yang tidak diabaikan Git; file yang sebagian staged dihitung sekali. Format yang ditulis eksplisit selalu menang. `commitpln` tetap default standard. `--scope`, `--type`, dan `--issue` dapat dipakai jika sesuai diff. `commitmsg` menggunakan staged changes jika sudah ada; ketika index kosong, satu pekerjaan yang jelas dapat di-stage lalu di-commit. Gunakan `--all` untuk seluruh perubahan nonignored, atau `--files` untuk path terpilih. `commitpln --source description "..."` hanya membuat draft, tidak membuat commit berdasarkan deskripsi saja.

Format **standard** memakai subject Conventional Commit yang merangkum tujuan perubahan, satu baris kosong, kemudian poin `-` dengan rincian yang berbeda dan terbukti pada diff, tanpa label `Changes:`. Untuk banyak perubahan terkait, subject mewakili semua poin. Perubahan yang tidak terkait sebaiknya dipisah menjadi beberapa commit.

```text
fix(auth): prevent duplicate login submissions

- Guard the submit handler while the request is pending
- Restore the button state when authentication finishes

---

fix(auth): cegah pengiriman login berulang

- Blokir handler pengiriman selama permintaan berlangsung
- Pulihkan status tombol saat autentikasi selesai
```

Untuk perubahan kecil pada `.gitignore`, nama berkas yang ditambahkan tidak perlu diulang di body. Jika hanya satu file berubah dan `--format` tidak diberikan, otomatis gunakan short, misalnya `chore(git): reduce accidental tracking of local setup files`. Klaim keamanan hanya digunakan bila pola yang diabaikan memang menyasar kredensial atau data sensitif; `.gitignore` tidak menghentikan pelacakan berkas yang sudah masuk index dan bukan jaminan rahasia tidak akan ter-commit. Untuk sejumlah perubahan terkait, contoh subject `feat(lessons): streamline publishing and progress tracking` dapat mencakup bullet pratinjau draf, pencatatan progres, dan tampilan rekap. Gunakan hanya rincian yang benar-benar ada di diff.

Contoh: satu file `.gitignore` yang berubah → short; `.gitignore` staged tetapi file lain masih unstaged → standard; satu file dengan `--format detailed` → detailed. Seleksi file untuk commit tetap mengikuti `--source`, `--files`, dan staged changes; aturan format tidak menambah file ke commit.

`both` menghasilkan **satu** commit dengan dua versi setara yang dipisah `---`; trailer bersama muncul sekali di akhir. Format short hanya subject; detailed menambah alasan dan dampak jika dapat dibuktikan dari perubahan aktual. Jumlah poin standard mengikuti isi diff. Agent tidak boleh mengarang hasil tes, issue, atau alasan bisnis.

## Versioning dan GitHub Release

**gitrelease** mendukung **semua proyek selain website dan aplikasi web berbasis browser**, termasuk mobile/desktop, CLI, tooling, installer, library, skrip, service dan backend API. Build, packaging dan distribusi mengikuti codebase serta kebutuhan proyek, tetap di dalam satu skill Git Workflow. Format changelog mengacu pada [TonzToon Komik](https://github.com/AlvinPradanaAntony/tonztoon_komik-vibecode/blob/main/CHANGELOG.md) dan alur publikasinya mengacu pada [build-release.yml](https://github.com/AlvinPradanaAntony/tonztoon_komik-vibecode/blob/main/.github/workflows/build-release.yml). Repo tersebut hanya menjadi referensi struktur; tujuan command adalah repo proyek yang sedang Anda gunakan.

```text
/git-workflow gitrelease
/git-workflow gitrelease init --version 0.1.0
/git-workflow gitrelease prepare --bump minor
/git-workflow gitrelease publish --version 1.1.0 --route workflow
```

Di Codex, ganti awalan dengan `$git-workflow`. Nilai versi di atas hanya contoh. `init` berarti memulai versioning proyek, bukan menjalankan git init atau menghapus riwayat versi yang sudah ada.

| Aksi | Cakupan |
| --- | --- |
| `init` | Validasi/inisialisasi versi dan changelog, lalu buat/lengkapi konfigurasi packaging, workflow build/release serta helper proyek untuk target yang dipilih. Mengikuti pola proyek yang jelas; bertanya hanya bila ada keputusan material. Lokal, tanpa commit/tag/push/dispatch. |
| `prepare` | Periksa perubahan Git/codebase, versi, changelog dan kesiapan pipeline; tentukan versi dari bukti, tanyakan keputusan penting yang belum jelas, lalu perbarui metadata/changelog lokal. Tanpa staging, commit, tag, push atau dispatch otomatis. |
| `publish` | Publikasikan versi yang telah disetujui dan di-commit beserta distribusi terverifikasi sesuai jenis produk dan target yang dipilih; gunakan workflow yang sesuai atau publikasi langsung. `--replace-existing` memilih penggantian tag/release versi yang sama dengan prosedur khusus. |
| `delete` | Hapus release/tag yang dipilih secara eksplisit dengan `--tag`; `--delete-scope release\|tag\|both` default both. Tidak publish, bump versi, atau push branch. |

| Parameter | Fungsi |
| --- | --- |
| `--version VERSION` atau `--bump patch\|minor\|major` | Pilih versi tepat atau usulan kenaikan; keduanya tidak boleh digabung. Suffix seperti `-alpha.1`, `-beta.1`, atau `-rc.1` menunjukkan prerelease. |
| `--from TAG_OR_SHA` | Tentukan baseline perubahan yang telah diverifikasi. |
| `--component PATH` | Pilih produk non-web pada monorepo; hanya batas rilis dan field versi terkait yang diperbarui. Frontend browser dan produk lain tidak dirilis secara implisit. |
| `--build-number N` | Pilih build counter native bila memang diperlukan; perhatikan counter yang diatur CI. |
| `--remote NAME`, `--branch NAME`, `--tag NAME` | Tentukan target publikasi dan nama tag; tanpa nilai, gunakan konteks repo yang terverifikasi. |
| `--route auto\|workflow\|direct` | Pilih pemilik publikasi; auto mendeteksi pipeline yang sesuai. |
| `--workflow PATH` | Pada init dapat menentukan file baru .github/workflows/*.yml atau *.yaml yang terverifikasi; aksi lain memilih workflow yang sudah ada. |
| `--draft` | Minta draft GitHub Release; tetap merupakan perubahan di GitHub. Workflow harus mendukungnya. |
| `--assets PATH...` | Berkas distribusi terverifikasi untuk rute direct bila diperlukan. Source release yang dipilih secara sengaja dapat tanpa upload binary; workflow mengikuti keluaran wajib proyek. |
| `--replace-existing` | Khusus publish: ganti tag/release yang sesuai versi proyek yang sudah disiapkan, setelah pemeriksaan dan persetujuan konkret. |
| `--delete-scope release\|tag\|both` | Khusus delete dengan --tag wajib; default both. Release menghapus GitHub Release/aset, tag menghapus tag lokal dan remote. Delete hanya menerima --tag, --delete-scope, --remote, --component. |

### Init menyiapkan alur build dan release

`gitrelease init` kini mencakup metadata versi/changelog **dan** penyiapan build/distribusi produk. Agent membaca entrypoint atau public exports, runtime/target, toolchain/lockfile, perintah build/validasi, packaging, signing bila berlaku, dan CI. Ia mempertahankan workflow lengkap yang sudah sesuai, atau membuat/melengkapi workflow yang belum tersedia. Nama/path/sumber versi dan format paket yang jelas dari pola proyek ditentukan tanpa pertanyaan rutin. Website tidak otomatis diubah menjadi desktop app.

Default route auto memakai publisher yang ada; jika belum ada dan cakupan produk dan distribusi jelas, agent membuat workflow GitHub Actions lokal. Route workflow menyiapkan workflow; route direct menyiapkan packaging/build lokal tanpa menambahkan publisher otomatis kedua. Jika tag yang sama masih memicu publisher otomatis yang sudah ada, agent menyelesaikan cakupan bypass/nonaktif yang ditinjau sebelum menyatakan route direct siap. Metadata versi dan changelog yang sudah valid tetap dipertahankan kecuali penggantian dipilih.

Target mengikuti distribusi proyek: paket aplikasi mobile/desktop, binary CLI, paket library, berkas installer/skrip, paket/container service, atau source bertag sesuai kontrak proyek. Kompilasi hanya dilakukan bila dibutuhkan; library/skrip tidak dipaksa memakai native bundler. Android/iOS dan desktop tetap mengikuti kebutuhan signing serta format installer/portable yang benar-benar didukung dan dipilih. Agent tidak mengaktifkan semua OS hanya karena framework mampu. Jika pilihan platform, format, signing atau publisher belum jelas, ia memberi opsi spesifik beserta manfaat/konsekuensi/cakupan dan satu Rekomendasi. Ia menahan hanya konfigurasi yang bergantung pada jawaban; pekerjaan metadata/helper yang sudah diizinkan dapat dilanjutkan secara independen.

Workflow yang dihasilkan memiliki pemeriksaan tag/versi/changelog, validasi/build/packaging sesuai produk, verifikasi keluaran dan signing bila berlaku, serta satu publisher yang menunggu seluruh pemeriksaan wajib berhasil. Source-only memakai validasi source dan tag/SHA tanpa job upload kosong. Keluaran wajib yang kosong/hilang menggagalkan publikasi; tidak ada fallback debug/unsigned untuk target yang membutuhkan signing. Release notes mengikuti layout TonzToon dengan entri versi yang tepat dan tabel Download. Helper yang dipakai CI disalin ke lokasi proyek yang nyata, bukan menunjuk skill global. Suffix prerelease termasuk alpha dikenali secara benar.

Init tidak membuat signing key, menulis secret GitHub, menginstal toolchain secara global, melakukan commit/tag/push, atau memicu build CI. Kebutuhan secret/runners disampaikan tanpa meminta nilai rahasia di chat. Konfigurasi yang selesai tidak berarti distribusi sudah terverifikasi: agent melaporkan validasi aktual, build/packaging yang belum dijalankan dan hambatan yang berlaku. Keluaran dibuat melalui workflow atau build/packaging lokal yang diminta; source-only memvalidasi source serta referensi tag/SHA tanpa membuat binary.

Setelah setup selesai: tinjau/commit file yang relevan, lalu publish ketika siap. Untuk pengembangan berikutnya, gunakan prepare, commitmsg, publish; prepare mengikuti pipeline yang sudah dibuat dan tidak membuat workflow baru setiap rilis.

### Prepare mencakup pemeriksaan dan keputusan versi

Aksi yang tersedia hanya `init`, `prepare`, `publish`, dan `delete`. Tanpa aksi, gitrelease menampilkan petunjuk keempat aksi tersebut tanpa memeriksa atau mengubah repo. Aksi tidak dikenal ditolak, bukan dialihkan diam-diam ke prepare.

```text
/git-workflow gitrelease prepare
```

Prepare membaca perubahan committed sejak baseline release yang relevan serta perubahan staged/unstaged/untracked yang layak; memeriksa versi proyek, changelog, pipeline/distribusi serta signing bila berlaku; lalu menentukan major/minor/patch dari kompatibilitas dan perilaku kode yang nyata, termasuk public API, CLI flags/output/exit codes, konfigurasi, installer/update, protokol service dan data. Ia tidak hanya mengandalkan prefix commit atau jumlah file. Jika pola proyek dan dampaknya jelas, ia menerapkan pembaruan lokal tanpa pertanyaan rutin. Jika versi bertentangan, kompatibilitas belum jelas atau keputusan penting lain belum tersedia, ia bertanya spesifik dan menunggu untuk bagian yang bergantung pada jawaban.

Versi yang sudah disiapkan tidak dinaikkan lagi ketika perintah diulang. Jika tidak ada perubahan yang layak dirilis, versi dipertahankan. Aset yang belum dibangun atau secret CI yang belum tersedia dapat dilaporkan sebagai hambatan publikasi tanpa menghalangi pembaruan metadata lokal yang sudah jelas. Setup pipeline yang belum ada ditangani melalui init atau perbaikan terpisah yang diizinkan. Prepare tidak melakukan commit/tag/push atau publish.

Alur pengembangan: **prepare → commitmsg → publish**. Jika Anda secara eksplisit meminta pemeriksaan/draft saja, agent memberikan proposal read-only sesuai permintaan tanpa aksi/parameter khusus tambahan.

### Publish sekali permintaan

```text
/git-workflow gitrelease publish
/git-workflow gitrelease publish --replace-existing
/git-workflow gitrelease delete --tag v1.25.0
/git-workflow gitrelease delete --tag v1.25.0 --delete-scope tag
/git-workflow gitrelease delete --tag v1.25.0 --delete-scope release
```

Masing-masing baris adalah satu request agent, bukan argumen installer. Versi dan prefix tag untuk publish berasal dari metadata yang sudah di-commit; target remote/branch mengikuti konfigurasi yang terverifikasi. Normal publish tidak menghapus tag/release lama. `--replace-existing` hanya mengganti tag/release untuk versi yang sama, bukan menghapus versi terdahulu yang berbeda. Installer `--replace` berbeda fungsinya.

Agent boleh menampilkan urutan operasi dalam satu baris dengan pemisah `;`, tetapi itu adalah preview. Ia mengeksekusi operasi secara berurutan dan memeriksa hasil setiap tahap. `;` saja tidak menghentikan perintah berikutnya ketika sebelumnya gagal; rangkaian shell yang benar-benar diminta harus memiliki guard sesuai shell. Bash dapat memakai `&&`, sedangkan PowerShell perlu pemeriksaan exit code native atau padanan yang didukung. Prompt user tidak dijalankan mentah sebagai kode shell.

Untuk publish normal: periksa commit/versi/changelog/pipeline/aset dan persetujuan, buat annotated tag pada SHA yang dipilih, push branch normal jika diperlukan, lalu push tag setelah tahap branch berhasil. Agent memantau workflow atau membuat release direct dengan distribusi yang telah diverifikasi. Source-only memerlukan tag/SHA, validasi dan petunjuk pengambilan source yang terverifikasi, tanpa aset binary wajib. Ia tidak melakukan force push branch. Penolakan menghentikan tahap selanjutnya yang bergantung pada push; agent memeriksa penyebab dan meminta keputusan spesifik bila diperlukan.

### Menghapus atau mengganti release/tag

Delete membutuhkan tag eksplisit; tanpa tag, agent menanyakan target dan tidak otomatis memilih release terbaru. Penghapusan release berbeda dari penghapusan tag: release mencakup catatan/aset GitHub, sedangkan scope tag mencakup ref tag lokal dan remote. Branch dengan nama sama tetap tidak disentuh. Delete tidak memerlukan paket aplikasi baru, tetapi tetap memeriksa identitas proyek, hak akses, perlindungan dan objek yang dipilih.

Sebelum menghapus, agent menunjukkan repo/tag, SHA/objek tag lokal dan remote, Release/aset yang terdampak, serta konsekuensi terhadap tautan unduhan. Ia menyimpan backup terverifikasi di luar worktree: ref pemulihan untuk objek tag/commit asli, metadata release, serta semua aset bila release akan dihapus. Backup tidak menjamin pengembalian ID release, jumlah unduhan, attestations atau seluruh metadata layanan. Backup yang gagal menghentikan penghapusan. Jika cakupan destruktif tersebut belum disetujui secara konkret, agent meminta keputusan; persetujuan yang sudah mencakup keadaan yang sama tidak diulang.

Untuk replacement, semua prasyarat publish harus siap **sebelum penghapusan**. Branch yang perlu dikirim harus dipush biasa dan berhasil terlebih dahulu. Setelah itu: hapus Release yang disetujui jika ada; hapus hanya tag remote yang masih menunjuk objek lama yang diperiksa; hapus tag lokal secara bersyarat; buat annotated tag baru pada SHA yang disetujui; push tag hanya bila nama itu masih kosong; lanjutkan satu publisher dan verifikasi aset. Jika tag berubah, push ditolak, aset/auth belum siap, atau salah satu tahap gagal, agent berhenti dan melaporkan tahap yang sudah selesai. Tidak ada `git push ... -f`, pergantian target diam-diam, atau penghapusan ulang sebagai retry otomatis. Rangkaian ini bukan transaksi atomik.

Untuk rilis stabil yang telah didistribusikan dengan kode berbeda, agent biasanya merekomendasikan versi patch baru dibanding mengganti versi yang sama, dengan alasan dan opsi mempertahankan/menunda. Anda tetap dapat memilih replacement yang diperbolehkan setelah meninjau dampaknya. Pada immutable release, GitHub melarang penggunaan ulang nama tag bahkan setelah release dihapus: agent harus memblokir replacement **sebelum** menghapus, lalu menawarkan versi baru atau menunda. Pengaturan perlindungan tidak diubah otomatis.

### Pilihan interaktif

Agent membaca repo sebelum bertanya. Opsi **menyesuaikan kondisi aktual**, bukan daftar pertanyaan tetap. Agent tidak menanyakan keputusan rutin yang sudah jelas dari argumen, persetujuan sebelumnya, atau pola proyek yang konsisten: misalnya sumber versi, lokasi changelog, prefix tag, target packaging, dan workflow release. Ia menjelaskan keputusan yang diambil beserta buktinya. Pola proyek menentukan cara menjalankan aksi, tetapi tidak otomatis mengizinkan commit tambahan, perubahan target distribusi, atau publikasi.

Pertanyaan diajukan hanya jika ada ambiguitas yang berdampak pada hasil atau tindakan berikutnya belum diizinkan. Contohnya versi proyek bertentangan dengan changelog, dampak kompatibilitas belum jelas, beberapa produk/publisher sama-sama cocok, perubahan cakupan platform, atau commit/tag/publish di luar cakupan yang disetujui. `--version`/`--bump` atau kebijakan versi proyek yang jelas dapat menyelesaikan pilihan versi lokal tanpa pertanyaan ulang. Pada `prepare`, agent menentukan dan menerapkan versi berdasarkan perubahan nyata jika kompatibilitas dan kebijakan proyek jelas; tidak perlu menanyakan pilihan patch/minor/major secara rutin.

Setiap pertanyaan menyebut **keputusan spesifik**, nilai/file/target aktual, dan alasan mengapa perlu jawaban. Opsi yang layak menjelaskan **manfaat**, **konsekuensi**, serta **cakupan file/remote**; tepat satu ditandai **Rekomendasi** dengan alasan dari bukti repo. Sertakan **Pertahankan kondisi sekarang / Tunda** bila layak. Jangan memaksakan semua opsi patch/minor/major atau platform yang tidak didukung.

Agent menunggu jawaban sebelum menjalankan bagian yang memerlukan persetujuan. Pekerjaan independen yang sudah diizinkan boleh dilanjutkan selama tidak menentukan keputusan yang belum dijawab. Jika keputusan menjadi prasyarat, agent menjelaskan apa yang terblokir dan apa yang masih bisa dilakukan. Misalnya konflik versi memblokir pengubahan metadata dan pembuatan tag; pemeriksaan workflow yang read-only masih dapat dilanjutkan. Jika user secara eksplisit meminta pemeriksaan/draft saja, agent tetap read-only tanpa mengedit file, fetch, build atau mutasi Git/GitHub. Diam atau waktu yang berlalu bukan persetujuan.

Jika versi proyek sudah lebih tinggi dari release terakhir, agent memeriksa apakah versi itu sedang disiapkan agar tidak melakukan bump dua kali. File/release notes dibuat konkret dalam cakupan yang telah diizinkan sebelum meminta keputusan publikasi. Persetujuan yang sudah mencakup versi/SHA/tag/rute/target yang sama tidak diminta ulang; perubahan cakupan dinilai kembali.

Contoh pertanyaan saat ditemukan ketidaksesuaian: “`pubspec.yaml` sudah 1.4.0, tetapi entri terbaru changelog masih 1.3.2. Apakah kita melengkapi changelog untuk 1.4.0 yang sedang disiapkan, atau mempertahankan keadaan sekarang? **Rekomendasi:** lengkapi 1.4.0 karena diff berisi fitur kompatibel dan versi itu belum diterbitkan. Perubahan hanya pada changelog lokal; commit dan tag belum termasuk.” Contoh ini dipakai hanya bila fakta tersebut benar pada repo yang diperiksa.

### Format CHANGELOG.md

Jika `CHANGELOG.md` atau `changelog.md` sudah ada, gunakan file tersebut. Jika belum ada, buat `CHANGELOG.md`. Struktur mengikuti referensi: pengantar proyek, bahasa Indonesia, header `## [versi] - YYYY-MM-DD`, kategori berbahasa Inggris dan poin `-`. Hanya kategori yang berisi perubahan nyata ditampilkan: Added, Changed, Fixed, Removed, Security, dan Notes. Riwayat lama tetap disimpan. Perubahan layout yang sudah ada ditampilkan sebagai diff untuk dipilih, termasuk opsi mempertahankan layout.

```markdown
# Changelog

Semua perubahan penting pada proyek **Nama Proyek** akan didokumentasikan di dalam file ini.

**Nama Proyek** adalah aplikasi desktop untuk mengelola kegiatan tim.

---

## [1.1.0] - 2026-10-01

### Added
- Filter status tugas pada daftar pekerjaan untuk memudahkan pemantauan tim.

### Fixed
- Memperbaiki pengiriman formulir berulang saat permintaan masih berlangsung.

---
```

Contoh isi di atas harus diganti sesuai perubahan aktual. GitHub Release mengambil versi yang dipilih secara tepat, dengan maksimal satu versi sebelumnya dalam `<details>` berjudul **Riwayat versi sebelumnya**. Catatan versi yang sudah diterbitkan tidak ditulis ulang dan riwayat changelog tidak dihapus demi mempersingkat release notes.

### Proyek dan distribusi yang didukung

| Jenis proyek | Distribusi dan pemeriksaan |
| --- | --- |
| Mobile/desktop | Paket installable/portable untuk OS/arsitektur yang dipilih. Android: APK signing release; iOS: IPA dengan signing/metode distribusi valid; Windows: EXE/MSI/portable ZIP; Linux: AppImage/DEB/RPM/portable; macOS: DMG/PKG/app ZIP sesuai signing/notarization. |
| CLI / tooling | Binary/arsip, paket runtime, skrip atau source sesuai implementasi. Periksa entrypoint, versi, runtime dan target yang memang digunakan; tidak wajib matrix semua OS. |
| Installer | Paket installer atau skrip/bundle dengan resource dan petunjuk penggunaan yang benar; validasi syntax/path dan tes terisolasi bila mengubah sistem. |
| Library | Paket ekosistem, arsip source atau source bertag sesuai pola proyek; periksa public exports, isi paket dan tes relevan. Tidak wajib executable. |
| Skrip / automation | Berkas skrip, arsip atau source bertag beserta runtime/dependensi; periksa syntax dan perilaku secara aman tanpa memicu automation produksi. |
| Service / backend API | Binary/paket, container atau source sesuai pola proyek; periksa runtime/config, tes service dan versi/digest untuk referensi image yang sudah tersedia. HTTP/API tetap didukung. |
| Produk non-web lainnya | Distribusi serta validasi mengikuti kontrak nyata proyek; tanyakan hanya keputusan penting yang belum dapat ditentukan dari codebase. |

Agent mengklasifikasikan produk dari entrypoint/public exports, manifest, build scripts, dokumentasi dan distribusi. Bahasa, framework, `package.json`, atau endpoint HTTP saja tidak menentukan cakupan. Library tetap didukung walaupun dipakai aplikasi browser. Electron/Tauri termasuk desktop ketika produk memang dikemas sebagai aplikasi desktop. Website, SPA, aplikasi SSR browser dan PWA sebagai produk rilis berada di luar cakupan; proses server-rendering tidak otomatis dianggap backend terpisah. Website tidak dibungkus menjadi desktop untuk melewati batas ini.

Pada monorepo campuran, `--component` atau konvensi proyek memilih batas rilis non-web. Shared dependencies dan field versi yang terbukti terkait dapat ikut diproses, sedangkan frontend browser atau produk independen tidak ikut dirilis. Jika batas versi/distribusi tidak dapat dipisahkan dengan jelas, agent menanyakan keputusan tersebut sebelum perubahan yang bergantung padanya.

Sumber versi mengikuti proyek: pubspec/Gradle/Xcode, package.json beserta field lockfile yang relevan, Cargo/workspace, metadata .NET, pyproject/version module/konstanta skrip, VERSION atau versi dari tag/linker. `go.mod` tidak diberi field versi buatan dan module path tidak diubah otomatis. Hanya field yang terbukti terkait diperbarui; build counter native terpisah dari versi rilis dan tidak diwajibkan pada proyek yang tidak menggunakannya.

Init/prepare dapat menyiapkan metadata sebelum keluaran distribusi selesai. Untuk app mobile/desktop, publish tetap memerlukan paket installable/portable pada semua target wajib. Untuk library/skrip atau produk lain dengan distribusi source yang memang dipilih, source bertag atau arsip source otomatis dapat digunakan; periksa tag/SHA, tes/syntax/package checks dan petunjuk pengambilan. Tidak perlu upload binary atau job artefak kosong. Checksum/debug symbols saja tidak menggantikan keluaran produk yang diwajibkan.

Distribusi source tidak dipilih diam-diam untuk mengatasi build gagal. Jika target binary wajib gagal, publikasi berhenti sampai target diperbaiki, atau cakupan target lebih kecil disetujui secara konkret. Platform yang belum berhasil dibangun tidak diiklankan sebagai tersedia.

Rute direct memerlukan file distribusi wajib yang ada, tidak kosong, benar versi/target dan berasal dari SHA release. Source-only memerlukan source/ref yang terverifikasi. Rute workflow memeriksa seluruh gate validasi/build/packaging sebelum publisher, lalu memverifikasi distribusi aktual. Draft dan replacement mengikuti persyaratan distribusi yang sama. Tabel Download mencantumkan filename/link nyata, runtime/instalasi dan batasan distribusi; source-only mencantumkan link source/tag serta cara mengambilnya, bukan tabel kosong atau binary fiktif.

`gitrelease` menerbitkan GitHub Release/tag. Publish ke npm/PyPI/crates/container registry, upload app store, deploy service dan perubahan konfigurasi remote memerlukan cakupan instruksi terpisah. Release dapat menautkan paket/image yang sudah tersedia setelah versi/digest-nya diverifikasi. Jika workflow release sekaligus melakukan registry publish/deploy yang belum diizinkan, agent menyiapkan rute terpisah atau meminta keputusan untuk cakupan konkret itu sebelum trigger/tag push. Semua trigger yang relevan diperiksa, termasuk workflow yang berjalan saat GitHub Release dibuat.

Rute workflow tidak berjalan bersamaan dengan publisher direct untuk tag yang sama. Workflow yang langsung publish tidak menjadi draft hanya dengan menambahkan `--draft`; agent menawarkan adaptasi yang ditinjau atau penundaan. Publisher mengenali suffix prerelease termasuk alpha. Retry melanjutkan tahap yang belum selesai tanpa bump ulang, memindahkan tag yang sudah diterbitkan atau membuat release duplikat. Publish direct memerlukan tool GitHub yang mendukung release atau `gh`/API yang terautentikasi di lingkungan pengguna.

### Contoh untuk proyek non-web

Jalankan sebagai pesan kepada agent, bukan argumen installer:

```text
/git-workflow gitrelease init
/git-workflow gitrelease prepare --component packages/cli
/git-workflow gitrelease publish --route direct --assets dist/tool-windows-amd64.zip
/git-workflow gitrelease publish --route direct
```

Baris terakhir sesuai untuk library/skrip dengan distribusi source-only yang sudah ditetapkan dan divalidasi; menghilangkan `--assets` tidak otomatis memilih mode source-only. Semua nama/path/target pada contoh harus disesuaikan dengan bukti proyek. Alur utamanya tetap **init → prepare → commitmsg → publish**, dengan init hanya diperlukan untuk setup atau melengkapi pipeline.

## Perlindungan perubahan

Preview tidak mengubah repository. Commit menjaga partial staging. Undo dan reset tidak mengubah remote secara otomatis. Hard reset membutuhkan target yang jelas, snapshot perubahan yang berisiko hilang, dan persetujuan untuk kehilangan konkret. Keep merge dapat menyisakan conflict marker dan menghasilkan commit biasa tanpa parent merge. Amend hanya memakai staged changes; jika push gagal sesudah amend, retry push tidak mengulang amend. Target push diperiksa lebih dulu; rewrite published tip menggunakan lease dengan SHA remote yang telah diverifikasi, tidak menggunakan plain `--force`.

Skills adalah instruksi agent; izin host, Git hooks, branch protection dan aturan proyek tetap berlaku. Pengujian paket dilakukan pada repository contoh di Linux, termasuk partial staging, merge cancel, amend-push, dan migrasi rule versi 2.3. Anda telah menguji versi sebelumnya di Antigravity IDE 2.0; struktur rule versi 2.4 belum diuji langsung di GUI Windows/Antigravity.

Referensi: [Codex Skills](https://learn.chatgpt.com/docs/build-skills), [Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [Antigravity Skills](https://antigravity.google/docs/skills), [Antigravity Rules](https://antigravity.google/docs/rules), [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/), [Git reset](https://git-scm.com/docs/git-reset), [Git merge](https://git-scm.com/docs/git-merge), [Git push](https://git-scm.com/docs/git-push), [SemVer](https://semver.org/), [GitHub Release CLI](https://cli.github.com/manual/gh_release_create).
