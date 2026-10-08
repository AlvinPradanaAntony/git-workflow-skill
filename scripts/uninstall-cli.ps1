# Remove the current user's native CLI; installed agent skills are retained.
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA 'Programs\git-workflow\bin'),
    [switch]$NoPathUpdate
)

$ErrorActionPreference = 'Stop'
$resolvedInstallDir = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath(
    [Environment]::ExpandEnvironmentVariables($InstallDir)
)
$destinationDir = [IO.Path]::GetFullPath($resolvedInstallDir)
if ($destinationDir.Contains(';')) { throw 'InstallDir cannot contain the PATH separator (;).' }
$destination = Join-Path $destinationDir 'git-workflow.exe'
$receiptPath = Join-Path $destinationDir '.git-workflow-cli.json'
$pathAdded = $false
if (Test-Path -LiteralPath $receiptPath) {
    $receipt = Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
    if ($receipt.schema -ne 1 -or $receipt.install_dir -ine $destinationDir -or
        $receipt.path_added -isnot [bool]) {
        throw 'Invalid CLI installation receipt. Review .git-workflow-cli.json before uninstalling.'
    }
    $pathAdded = $receipt.path_added
} elseif (-not $NoPathUpdate) {
    Write-Warning 'No CLI installation receipt found. Existing PATH entries are retained; remove a manually registered entry yourself if needed.'
}
if (-not $PSCmdlet.ShouldProcess($destination, 'Remove CLI and optionally unregister its owned user PATH entry')) {
    return
}

# Never delete the installation directory: it may contain other tools or skills.
if (Test-Path -LiteralPath $destination) {
    if (-not (Test-Path -LiteralPath $destination -PathType Leaf)) {
        throw 'The CLI executable path is not a file.'
    }
    Remove-Item -LiteralPath $destination -Force
}
if (-not $NoPathUpdate -and $pathAdded) {
    # Preserve all other raw entries, including empty entries and %VARIABLE% references.
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $remaining = @($userPath -split ';' | Where-Object { $_ -ine $destinationDir })
    $newUserPath = $remaining -join ';'
    if ($userPath -cne $newUserPath) {
        [Environment]::SetEnvironmentVariable('Path', $newUserPath, 'User')
    }
    $env:Path = (@($env:Path -split ';' | Where-Object { $_ -ine $destinationDir }) -join ';')
}
if (Test-Path -LiteralPath $receiptPath -PathType Leaf) {
    Remove-Item -LiteralPath $receiptPath -Force
}
Write-Output "Removed CLI (if installed): $destination"
if ($NoPathUpdate) { Write-Output 'PATH cleanup skipped.' }
Write-Output 'Installed agent skills are retained. Open a new terminal to refresh PATH.'
