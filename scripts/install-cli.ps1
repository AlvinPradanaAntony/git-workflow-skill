# Run from an extracted Windows release archive, as the current user.
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$InstallDir,
    [switch]$NoPathUpdate,
    [switch]$Yes,
    [switch]$NoPause
)

$ErrorActionPreference = 'Stop'

function Wait-CliExit {
    if ($Yes -or $NoPause -or $WhatIfPreference -or [Console]::IsInputRedirected) { return }
    try {
        Write-Host "`nTekan tombol apa saja untuk selesai..." -NoNewline
        $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
        Write-Host ''
    } catch {
        # Hosts without ReadKey (for example ISE) can still accept a line.
        try { Read-Host 'Tekan Enter untuk selesai' | Out-Null } catch { }
    }
}

# Finally also runs on validation errors, cancellation and early returns.
try {
if (-not $PSBoundParameters.ContainsKey('InstallDir')) {
    $InstallDir = if (Test-Path -LiteralPath (Join-Path $PSScriptRoot '.git-workflow-cli.json')) {
        $PSScriptRoot
    } else {
        Join-Path $env:LOCALAPPDATA 'Programs\git-workflow\bin'
    }
}
Write-Output ''
Write-Output '+--------------------------------------+'
Write-Output '|           Git Workflow CLI           |'
Write-Output '+--------------------------------------+'
Write-Output '  INSTALL CLI'
Write-Output ''
$cliTick = '[OK]'
if ([Console]::OutputEncoding.CodePage -eq 65001) { $cliTick = [string][char]0x2713 }
$source = Join-Path $PSScriptRoot 'git-workflow.exe'
if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
    throw 'git-workflow.exe must be beside this script. Extract the complete Windows release archive first.'
}
$resolvedInstallDir = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath(
    [Environment]::ExpandEnvironmentVariables($InstallDir)
)
$destinationDir = [IO.Path]::GetFullPath($resolvedInstallDir)
if ($destinationDir.Contains(';')) {
    throw 'InstallDir cannot contain the PATH separator (;).'
}
$destination = Join-Path $destinationDir 'git-workflow.exe'
$packageFiles = @('git-workflow.exe', 'install-cli.ps1', 'uninstall-cli.ps1', 'README.md', 'Panduan-Git-Workflow.md')
if ($destinationDir.TrimEnd('\') -eq [IO.Path]::GetPathRoot($destinationDir).TrimEnd('\')) {
    throw 'InstallDir must not be a filesystem root.'
}
$sourceDir = [IO.Path]::GetFullPath($PSScriptRoot)
if (Test-Path -LiteralPath (Join-Path $sourceDir '.git')) {
    throw 'Run the installer from an extracted release archive, not a repository root.'
}
foreach ($name in $packageFiles) {
    $item = Get-Item -LiteralPath (Join-Path $sourceDir $name) -ErrorAction Stop
    if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Package member must be a regular file: $name. Extract the complete release archive first."
    }
}
$receiptPath = Join-Path $destinationDir '.git-workflow-cli.json'
$pathAdded = $false
$ownsPackage = $false
if (Test-Path -LiteralPath $receiptPath) {
    if ((Get-Item -LiteralPath $receiptPath).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw 'The CLI installation receipt must not be a link.'
    }
    $receipt = Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
    if ($receipt.schema -ne 1 -or $receipt.install_dir -ine $destinationDir -or
        $receipt.path_added -isnot [bool]) {
        throw 'Invalid CLI installation receipt. Review .git-workflow-cli.json before reinstalling.'
    }
    $pathAdded = $receipt.path_added
    if ($null -ne $receipt.files) {
        if (@($receipt.files).Count -ne $packageFiles.Count -or
            (Compare-Object $packageFiles @($receipt.files))) {
            throw 'Invalid CLI package file list in the installation receipt.'
        }
        $ownsPackage = $true
    }
}
foreach ($name in $packageFiles) {
    $target = Join-Path $destinationDir $name
    if (Test-Path -LiteralPath $target) {
        $item = Get-Item -LiteralPath $target
        if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw "Destination package member must be a regular file: $target"
        }
        if ($sourceDir -ine $destinationDir -and -not $ownsPackage -and $name -ne 'git-workflow.exe') {
            throw "An unowned file already exists at $target. Choose another InstallDir."
        }
    }
}
Write-Output "Sumber : $sourceDir"
Write-Output "Tujuan : $destinationDir"
Write-Output '[ ] Pindahkan seluruh isi paket release (cut):'
$packageFiles | ForEach-Object { Write-Output "    - $_" }
if ($NoPathUpdate) { Write-Output '[-] Pendaftaran PATH dilewati (-NoPathUpdate).' }
else { Write-Output '[ ] Daftarkan user PATH bila diperlukan.' }
Write-Output '[ ] Simpan catatan kepemilikan PATH untuk uninstall.'
Write-Output 'Skill agent dipasang terpisah melalui git-workflow install.'
if (-not $PSCmdlet.ShouldProcess($destinationDir, 'Move the release package and optionally register user PATH')) {
    return
}
if (-not $Yes -and -not $PSBoundParameters.ContainsKey('Confirm')) {
    try { $cliAnswer = Read-Host 'Lanjutkan install CLI? [y/N]' }
    catch { throw 'Konfirmasi tidak tersedia. Gunakan -Yes untuk otomasi.' }
    if ($cliAnswer -notmatch '^(y|yes|ya)$') {
        Write-Output 'Operasi dibatalkan. Tidak ada perubahan.'; return
    }
}
Write-Output ''
Write-Output '[1/3] Memindahkan paket release...'
New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null
# Record the approved names before moving, so an interrupted move can be cleaned up.
@{ schema = 1; install_dir = $destinationDir; path_added = $pathAdded; files = $packageFiles } |
    ConvertTo-Json | Set-Content -LiteralPath $receiptPath -Encoding UTF8
foreach ($name in $packageFiles) {
    if ($sourceDir -ine $destinationDir) {
        Move-Item -LiteralPath (Join-Path $sourceDir $name) -Destination (Join-Path $destinationDir $name) -Force
    }
    Write-Output "$cliTick Paket terpasang: $name"
}
Write-Output "$cliTick Installed CLI: $destination"

Write-Output '[2/3] Memeriksa konfigurasi PATH...'
if (-not $NoPathUpdate) {
    # Preserve the raw user PATH, including existing %VARIABLE% references.
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $userEntries = @($userPath -split ';' | Where-Object { $_ })
    $registered = $false
    foreach ($entry in $userEntries) {
        if ([Environment]::ExpandEnvironmentVariables($entry).TrimEnd('\') -ieq $destinationDir.TrimEnd('\')) {
            $registered = $true
        }
    }
    if (-not $registered) {
        $newUserPath = if ($userPath) { $destinationDir + ';' + $userPath } else { $destinationDir }
        [Environment]::SetEnvironmentVariable('Path', $newUserPath, 'User')
        $pathAdded = $true
    }
    if (-not (@($env:Path -split ';') -contains $destinationDir)) {
        $env:Path = $destinationDir + ';' + $env:Path
    }
    Write-Output "$cliTick User PATH registered (atau sudah tersedia)."
} else {
    Write-Output '[-] PATH registration skipped.'
}
Write-Output '[3/3] Menyimpan catatan instalasi...'
@{ schema = 1; install_dir = $destinationDir; path_added = $pathAdded; files = $packageFiles } |
    ConvertTo-Json | Set-Content -LiteralPath $receiptPath -Encoding UTF8
Write-Output "$cliTick Catatan kepemilikan PATH tersimpan."
Write-Output ''
Write-Output "$cliTick Install CLI sukses."
Write-Output "Uninstall: & '$($destinationDir.Replace("'", "''"))\uninstall-cli.ps1' -InstallDir '$($destinationDir.Replace("'", "''"))'"
if ($NoPathUpdate) {
    Write-Output 'PATH registration skipped. Add the installation directory to PATH before using git-workflow by name.'
} else {
    Write-Output 'User PATH registered. Open a new terminal, then run: git-workflow --version'
}
} catch {
    Write-Host "[ERROR] Install CLI gagal: $($_.Exception.Message)" -ForegroundColor Red
    throw
} finally {
    Wait-CliExit
}
