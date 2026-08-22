#Requires -Version 5.1
<#
.SYNOPSIS
Unregisters and removes the current user's PDF Archiver for Thunderbird companion.
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$hostName = 'de.sokrates1989.thunderbird_pdf_archiver'
$registryKey = "HKCU:\Software\Mozilla\NativeMessagingHosts\$hostName"
if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    throw 'LOCALAPPDATA is unavailable; the per-user install directory cannot be resolved.'
}
$applicationRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $env:LOCALAPPDATA 'ThunderbirdPdfArchiver')
)
$localAppDataRoot = [System.IO.Path]::GetFullPath($env:LOCALAPPDATA).TrimEnd('\') + '\'
if (-not $applicationRoot.StartsWith($localAppDataRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'The resolved application directory escaped LOCALAPPDATA.'
}
$removed = $false

try {
    if ((Test-Path -LiteralPath $registryKey) -and
        $PSCmdlet.ShouldProcess($registryKey, 'Unregister Native Messaging host')) {
        Remove-Item -LiteralPath $registryKey -Force
        $removed = $true
    }
    if ((Test-Path -LiteralPath $applicationRoot) -and
        $PSCmdlet.ShouldProcess($applicationRoot, 'Remove all installed native-host versions')) {
        Remove-Item -LiteralPath $applicationRoot -Recurse -Force
        $removed = $true
    }
    if ($removed) {
        Write-Host 'PDF Archiver for Thunderbird native companion was removed for the current user.'
    }
    else {
        Write-Host 'No uninstall changes were made.'
    }
}
catch {
    Write-Error "Uninstall failed: $($_.Exception.Message)"
    throw
}
