# Remove the current user's native CLI; installed agent skills are retained.
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
Write-Output '  UNINSTALL CLI'
Write-Output ''
$cliTick = '[OK]'
if ([Console]::OutputEncoding.CodePage -eq 65001) { $cliTick = [string][char]0x2713 }
$resolvedInstallDir = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath(
    [Environment]::ExpandEnvironmentVariables($InstallDir)
)
$destinationDir = [IO.Path]::GetFullPath($resolvedInstallDir)
if ($destinationDir.Contains(';')) { throw 'InstallDir cannot contain the PATH separator (;).' }
$destination = Join-Path $destinationDir 'git-workflow.exe'
$receiptPath = Join-Path $destinationDir '.git-workflow-cli.json'
$pathAdded = $false
$packageFiles = @('git-workflow.exe', 'install-cli.ps1', 'uninstall-cli.ps1', 'README.md', 'Panduan-Git-Workflow.md')
$removeFiles = @('git-workflow.exe')
if ($destinationDir.TrimEnd('\') -eq [IO.Path]::GetPathRoot($destinationDir).TrimEnd('\')) {
    throw 'InstallDir must not be a filesystem root.'
}
if (Test-Path -LiteralPath $receiptPath) {
    if ((Get-Item -LiteralPath $receiptPath).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw 'The CLI installation receipt must not be a link.'
    }
    $receipt = Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
    if ($receipt.schema -ne 1 -or $receipt.install_dir -ine $destinationDir -or
        $receipt.path_added -isnot [bool]) {
        throw 'Invalid CLI installation receipt. Review .git-workflow-cli.json before uninstalling.'
    }
    $pathAdded = $receipt.path_added
    if ($null -ne $receipt.files) {
        if (@($receipt.files).Count -ne $packageFiles.Count -or
            (Compare-Object $packageFiles @($receipt.files))) {
            throw 'Invalid CLI package file list in the installation receipt.'
        }
        $removeFiles = $packageFiles
    }
} elseif (-not $NoPathUpdate) {
    Write-Warning 'No CLI installation receipt found. Existing PATH entries are retained; remove a manually registered entry yourself if needed.'
}
foreach ($name in $removeFiles) {
    $target = Join-Path $destinationDir $name
    if (Test-Path -LiteralPath $target) {
        $item = Get-Item -LiteralPath $target
        if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw "Installed package member must be a regular file: $target"
        }
    }
}
Write-Output "Tujuan : $destinationDir"
Write-Output '[ ] Hapus file paket yang tercatat, termasuk helper dan panduan:'
$removeFiles | ForEach-Object { Write-Output "    - $_" }
if ($NoPathUpdate) { Write-Output '[-] Pembersihan PATH dilewati (-NoPathUpdate).' }
elseif ($pathAdded) { Write-Output '[ ] Hapus entri user PATH milik installer.' }
else { Write-Output '[-] PATH yang tidak tercatat sebagai milik installer dipertahankan.' }
Write-Output '[ ] Hapus catatan instalasi jika tersedia.'
Write-Output 'Skill agent dan file lain tetap tersimpan.'
if (-not $PSCmdlet.ShouldProcess($destination, 'Remove CLI and optionally unregister its owned user PATH entry')) {
    return
}
if (-not $Yes -and -not $PSBoundParameters.ContainsKey('Confirm')) {
    try { $cliAnswer = Read-Host 'Lanjutkan uninstall CLI? [y/N]' }
    catch { throw 'Konfirmasi tidak tersedia. Gunakan -Yes untuk otomasi.' }
    if ($cliAnswer -notmatch '^(y|yes|ya)$') {
        Write-Output 'Operasi dibatalkan. Tidak ada perubahan.'; return
    }
}
Write-Output ''
Write-Output '[1/3] Menghapus paket CLI...'

# Remove only recorded package files; unrelated tools and skills stay intact.
foreach ($name in $removeFiles) {
    $target = Join-Path $destinationDir $name
    if (Test-Path -LiteralPath $target -PathType Leaf) {
        Remove-Item -LiteralPath $target -Force
    }
    Write-Output "$cliTick File paket sudah tidak ada: $name"
}
Write-Output "$cliTick Removed CLI (if installed): $destination"
Write-Output '[2/3] Memeriksa konfigurasi PATH...'
if (-not $NoPathUpdate -and $pathAdded) {
    # Preserve all other raw entries, including empty entries and %VARIABLE% references.
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $remaining = @($userPath -split ';' | Where-Object { $_ -ine $destinationDir })
    $newUserPath = $remaining -join ';'
    if ($userPath -cne $newUserPath) {
        [Environment]::SetEnvironmentVariable('Path', $newUserPath, 'User')
    }
    $env:Path = (@($env:Path -split ';' | Where-Object { $_ -ine $destinationDir }) -join ';')
    Write-Output "$cliTick Entri PATH milik installer dibersihkan."
} else {
    Write-Output '[-] PATH dipertahankan atau pembersihan dilewati.'
}
Write-Output '[3/3] Membersihkan catatan instalasi...'
if (Test-Path -LiteralPath $receiptPath -PathType Leaf) {
    Remove-Item -LiteralPath $receiptPath -Force
}
Write-Output "$cliTick Catatan instalasi sudah tidak ada."
# Remove only empty directories, never recursively delete a shared/custom bin.
if ((Test-Path -LiteralPath $destinationDir -PathType Container) -and
    @(Get-ChildItem -LiteralPath $destinationDir -Force).Count -eq 0) {
    if ($PWD.ProviderPath.TrimEnd('\') -ieq $destinationDir.TrimEnd('\')) {
        Set-Location -LiteralPath (Split-Path -Parent $destinationDir)
    }
    Remove-Item -LiteralPath $destinationDir -Force
    $defaultDir = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'Programs\git-workflow\bin'))
    $parentDir = Split-Path -Parent $destinationDir
    if ($destinationDir -ieq $defaultDir -and @(Get-ChildItem -LiteralPath $parentDir -Force).Count -eq 0) {
        if ($PWD.ProviderPath.TrimEnd('\') -ieq $parentDir.TrimEnd('\')) {
            Set-Location -LiteralPath (Split-Path -Parent $parentDir)
        }
        Remove-Item -LiteralPath $parentDir -Force
    }
    Write-Output "$cliTick Folder pemasangan kosong dibersihkan."
} elseif (Test-Path -LiteralPath $destinationDir -PathType Container) {
    Write-Output '[-] Folder dipertahankan karena masih berisi file lain.'
}
Write-Output ''
Write-Output "$cliTick Uninstall CLI sukses."
if ($NoPathUpdate) { Write-Output 'PATH cleanup skipped.' }
Write-Output 'Installed agent skills are retained. Open a new terminal to refresh PATH.'
} catch {
    Write-Host "[ERROR] Uninstall CLI gagal: $($_.Exception.Message)" -ForegroundColor Red
    throw
} finally {
    Wait-CliExit
}
