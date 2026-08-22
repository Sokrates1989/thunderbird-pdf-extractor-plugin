#Requires -Version 5.1
<#
.SYNOPSIS
Installs and registers the versioned native companion for the current user.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version = '1.1.0',

    [string]$ArtifactDirectory = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$hostName = 'de.sokrates1989.thunderbird_pdf_archiver'
$extensionId = 'thunderbird-pdf@felicitas-wisdom.com'
$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if ([string]::IsNullOrWhiteSpace($ArtifactDirectory)) {
    $ArtifactDirectory = Join-Path $repositoryRoot 'artifacts\native-host'
}
$sourceExecutable = Join-Path $ArtifactDirectory 'thunderbird-pdf-archiver-host.exe'
if (-not (Test-Path -LiteralPath $sourceExecutable -PathType Leaf)) {
    throw "Native-host artifact not found at '$sourceExecutable'. Run build.ps1 first."
}
$artifactVersion = (& $sourceExecutable '--version').Trim()
if ($LASTEXITCODE -ne 0 -or $artifactVersion -ne $Version) {
    throw "Native-host artifact version '$artifactVersion' does not match requested version '$Version'."
}
if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    throw 'LOCALAPPDATA is unavailable; the per-user install directory cannot be resolved.'
}

$applicationRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $env:LOCALAPPDATA 'ThunderbirdPdfArchiver')
)
$installDirectory = [System.IO.Path]::GetFullPath((Join-Path $applicationRoot $Version))
$expectedPrefix = $applicationRoot.TrimEnd('\') + '\'
if (-not $installDirectory.StartsWith($expectedPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'The resolved install directory escaped the application root.'
}
$installedExecutable = Join-Path $installDirectory 'thunderbird-pdf-archiver-host.exe'
$manifestPath = Join-Path $installDirectory "$hostName.json"
$registryKey = "HKCU:\Software\Mozilla\NativeMessagingHosts\$hostName"
$installed = $false
$registered = $false

try {
    if ($PSCmdlet.ShouldProcess($installDirectory, 'Install versioned native companion')) {
        New-Item -ItemType Directory -Path $installDirectory -Force | Out-Null
        Copy-Item -LiteralPath $sourceExecutable -Destination $installedExecutable -Force
        $sourceHash = (Get-FileHash -LiteralPath $sourceExecutable -Algorithm SHA256).Hash
        $installedHash = (Get-FileHash -LiteralPath $installedExecutable -Algorithm SHA256).Hash
        if ($sourceHash -ne $installedHash) {
            throw 'The installed native-host executable failed SHA-256 verification.'
        }
        $manifest = [ordered]@{
            name = $hostName
            description = 'Local searchable email and attachment PDF companion for Thunderbird.'
            path = $installedExecutable
            type = 'stdio'
            allowed_extensions = @($extensionId)
        }
        $manifestJson = $manifest | ConvertTo-Json -Depth 3
        $utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($manifestPath, $manifestJson, $utf8WithoutBom)
        $installed = $true
    }

    if ($PSCmdlet.ShouldProcess($registryKey, 'Register Thunderbird Native Messaging host')) {
        New-Item -Path $registryKey -Force | Out-Null
        Set-Item -Path $registryKey -Value $manifestPath
        $registered = $true
    }

    if ($installed -and $registered) {
        Write-Host "Installed native host version $Version for the current user."
        Write-Host "Manifest: $manifestPath"
    }
    else {
        Write-Host 'No installation changes were made.'
    }
}
catch {
    Write-Error "Installation failed: $($_.Exception.Message)"
    throw
}
