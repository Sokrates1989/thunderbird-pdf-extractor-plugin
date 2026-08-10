#Requires -Version 5.1
<#
.SYNOPSIS
Builds the Slice 2 XPI and signed-ready one-file Windows native host.
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

    Write-Host "XPI: $(Join-Path $artifactRoot 'thunderbird-pdf-archiver-0.2.2.xpi')"
    Write-Host "Native host: $(Join-Path $nativeArtifactRoot 'thunderbird-pdf-archiver-host.exe')"
}
catch {
    Write-Error "Build failed: $($_.Exception.Message)"
    throw
}
