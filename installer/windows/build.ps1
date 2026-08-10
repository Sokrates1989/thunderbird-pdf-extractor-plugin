#Requires -Version 5.1
<#
.SYNOPSIS
Builds the Slice 3 XPI, one-file Windows native host, and portable release ZIP.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch]$SkipDependencyInstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-CheckedCommand {
    <# Runs a native command and converts a non-zero exit code into a terminating error. #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$Executable,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command '$Executable' failed with exit code $LASTEXITCODE."
    }
}

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$extensionRoot = Join-Path $repositoryRoot 'extension'
$nativeRoot = Join-Path $repositoryRoot 'native-host'
$virtualEnvironment = Join-Path $nativeRoot '.venv'
$pythonExecutable = Join-Path $virtualEnvironment 'Scripts\python.exe'
$artifactRoot = Join-Path $repositoryRoot 'artifacts'
$nativeArtifactRoot = Join-Path $artifactRoot 'native-host'
$version = '0.3.0'
$xpiName = "thunderbird-pdf-archiver-$version.xpi"
$releaseName = "thunderbird-pdf-archiver-$version-windows"
$releaseArchive = Join-Path $artifactRoot "$releaseName.zip"
$releaseWorkRoot = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot 'build\release'))
$releaseDirectory = [System.IO.Path]::GetFullPath((Join-Path $releaseWorkRoot $releaseName))
$expectedReleasePrefix = $releaseWorkRoot.TrimEnd('\') + '\'
if (-not $releaseDirectory.StartsWith(
        $expectedReleasePrefix,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
    throw 'The resolved release staging directory escaped the repository build root.'
}
$pyInstallerWork = Join-Path $nativeRoot 'build\pyinstaller'
$pyInstallerSpec = Join-Path $nativeRoot 'build\spec'

if (-not $PSCmdlet.ShouldProcess($artifactRoot, 'Build extension and native-host artifacts')) {
    return
}

try {
    if (-not $SkipDependencyInstall) {
        Push-Location $extensionRoot
        try {
            Invoke-CheckedCommand -Executable 'npm.cmd' -Arguments @('ci')
        }
        finally {
            Pop-Location
        }

        if (-not (Test-Path -LiteralPath $pythonExecutable -PathType Leaf)) {
            Invoke-CheckedCommand -Executable 'python.exe' -Arguments @('-m', 'venv', $virtualEnvironment)
        }
        Invoke-CheckedCommand -Executable $pythonExecutable -Arguments @(
            '-m', 'pip', 'install', '--require-hashes', '-r', (Join-Path $nativeRoot 'requirements.lock')
        )
    }

    Push-Location $extensionRoot
    try {
        Invoke-CheckedCommand -Executable 'npm.cmd' -Arguments @('run', 'package')
    }
    finally {
        Pop-Location
    }

    New-Item -ItemType Directory -Path $nativeArtifactRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $pyInstallerWork -Force | Out-Null
    New-Item -ItemType Directory -Path $pyInstallerSpec -Force | Out-Null
    Push-Location $nativeRoot
    try {
        Invoke-CheckedCommand -Executable $pythonExecutable -Arguments @(
            '-m', 'PyInstaller',
            '--clean',
            '--noconfirm',
            '--onefile',
            '--name', 'thunderbird-pdf-archiver-host',
            '--distpath', $nativeArtifactRoot,
            '--workpath', $pyInstallerWork,
            '--specpath', $pyInstallerSpec,
            (Join-Path $nativeRoot 'main.py')
        )
    }
    finally {
        Pop-Location
    }

    & (Join-Path $PSScriptRoot 'build-setup.ps1') -Version $version

    if (Test-Path -LiteralPath $releaseDirectory) {
        Remove-Item -LiteralPath $releaseDirectory -Recurse -Force
    }
    New-Item -ItemType Directory -Path (Join-Path $releaseDirectory 'artifacts\native-host') -Force |
        Out-Null
    New-Item -ItemType Directory -Path (Join-Path $releaseDirectory 'installer\windows') -Force |
        Out-Null
    New-Item -ItemType Directory -Path (Join-Path $releaseDirectory 'docs') -Force | Out-Null

    Copy-Item -LiteralPath (Join-Path $artifactRoot $xpiName) -Destination (
        Join-Path $releaseDirectory 'artifacts'
    )
    Copy-Item -LiteralPath (
        Join-Path $nativeArtifactRoot 'thunderbird-pdf-archiver-host.exe'
    ) -Destination (Join-Path $releaseDirectory 'artifacts\native-host')
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'install.ps1') -Destination (
        Join-Path $releaseDirectory 'installer\windows'
    )
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'uninstall.ps1') -Destination (
        Join-Path $releaseDirectory 'installer\windows'
    )
    Copy-Item -LiteralPath (
        Join-Path $artifactRoot "Thunderbird-PDF-Archiver-Setup-$version-win-x64.exe"
    ) -Destination $releaseDirectory
    foreach ($fileName in @('README.md', 'README.de.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md')) {
        Copy-Item -LiteralPath (Join-Path $repositoryRoot $fileName) -Destination $releaseDirectory
    }
    foreach ($fileName in @(
            'testing.md',
            'troubleshooting.md',
            'security.md',
            'slice-3-acceptance.md',
            'windows-installer-testing.md'
        )) {
        Copy-Item -LiteralPath (Join-Path $repositoryRoot "docs\$fileName") -Destination (
            Join-Path $releaseDirectory 'docs'
        )
    }
    if (Test-Path -LiteralPath $releaseArchive) {
        Remove-Item -LiteralPath $releaseArchive -Force
    }
    Compress-Archive -Path (Join-Path $releaseDirectory '*') -DestinationPath $releaseArchive

    Write-Host "XPI: $(Join-Path $artifactRoot $xpiName)"
    Write-Host "Native host: $(Join-Path $nativeArtifactRoot 'thunderbird-pdf-archiver-host.exe')"
    Write-Host "Windows release: $releaseArchive"
    Write-Host "Windows setup: $(
        Join-Path $artifactRoot "Thunderbird-PDF-Archiver-Setup-$version-win-x64.exe"
    )"
}
catch {
    Write-Error "Build failed: $($_.Exception.Message)"
    throw
}
