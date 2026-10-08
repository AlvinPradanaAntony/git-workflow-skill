# Run from an extracted Windows release archive, as the current user.
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA 'Programs\git-workflow\bin'),
    [switch]$NoPathUpdate
)

$ErrorActionPreference = 'Stop'
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
$receiptPath = Join-Path $destinationDir '.git-workflow-cli.json'
$pathAdded = $false
if (Test-Path -LiteralPath $receiptPath) {
    $receipt = Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
    if ($receipt.schema -ne 1 -or $receipt.install_dir -ine $destinationDir -or
        $receipt.path_added -isnot [bool]) {
        throw 'Invalid CLI installation receipt. Review .git-workflow-cli.json before reinstalling.'
    }
    $pathAdded = $receipt.path_added
}
if (-not $PSCmdlet.ShouldProcess($destination, 'Install CLI and optionally register user PATH')) {
    return
}
New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null
if ([IO.Path]::GetFullPath($source) -ne $destination) {
    Copy-Item -LiteralPath $source -Destination $destination -Force
}

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
}
@{ schema = 1; install_dir = $destinationDir; path_added = $pathAdded } |
    ConvertTo-Json | Set-Content -LiteralPath $receiptPath -Encoding UTF8
Write-Output "Installed CLI: $destination"
if ($NoPathUpdate) {
    Write-Output 'PATH registration skipped. Add the installation directory to PATH before using git-workflow by name.'
} else {
    Write-Output 'User PATH registered. Open a new terminal, then run: git-workflow --version'
}
