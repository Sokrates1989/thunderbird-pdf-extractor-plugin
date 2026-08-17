#Requires -Version 5.1
<#
.SYNOPSIS
Compiles the per-user Windows setup from verified extension and native-host artifacts.
#>
[CmdletBinding()]
param(
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version = '0.5.0',

    [switch]$TestMode
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Find-InnoSetupCompiler {
    <# Resolve an explicitly configured or standard per-user/system Inno Setup compiler. #>
    $candidates = @()
    if (-not [string]::IsNullOrWhiteSpace($env:INNO_SETUP_COMPILER)) {
        $candidates += $env:INNO_SETUP_COMPILER
    }
    $command = Get-Command 'ISCC.exe' -ErrorAction SilentlyContinue
    if ($null -ne $command) {
        $candidates += $command.Source
    }
    $candidates += @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
        (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe')
    )
    foreach ($candidate in $candidates) {
        if (-not [string]::IsNullOrWhiteSpace($candidate) -and
            (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return [System.IO.Path]::GetFullPath($candidate)
        }
    }
    throw 'Inno Setup 6 was not found. Install JRSoftware.InnoSetup or set INNO_SETUP_COMPILER.'
}

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$artifactRoot = Join-Path $repositoryRoot 'artifacts'
$hostArtifact = Join-Path $artifactRoot 'native-host\thunderbird-pdf-archiver-host.exe'
$germanExtensionArtifact = Join-Path $artifactRoot "thunderbird-pdf-archiver-$Version-de.xpi"
$englishExtensionArtifact = Join-Path $artifactRoot "thunderbird-pdf-archiver-$Version-en.xpi"
foreach ($artifact in @($hostArtifact, $germanExtensionArtifact, $englishExtensionArtifact)) {
    if (-not (Test-Path -LiteralPath $artifact -PathType Leaf)) {
        throw "Required installer artifact not found at '$artifact'. Run build.ps1 first."
    }
}

$reportedHostVersion = (& $hostArtifact '--version').Trim()
if ($LASTEXITCODE -ne 0 -or $reportedHostVersion -ne $Version) {
    throw "Native-host artifact version '$reportedHostVersion' does not match '$Version'."
}

$compiler = Find-InnoSetupCompiler
$setupSource = Join-Path $PSScriptRoot 'setup.iss'
$arguments = @("/DAppVersion=$Version")
if ($TestMode) {
    $testOutput = Join-Path $repositoryRoot 'build\installer-test'
    New-Item -ItemType Directory -Path $testOutput -Force | Out-Null
    $arguments += '/DTestMode=1'
    $arguments += "/O$testOutput"
}
$arguments += $setupSource

& $compiler @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compilation failed with exit code $LASTEXITCODE."
}

if ($TestMode) {
    Write-Output (Join-Path $testOutput "Thunderbird-PDF-Archiver-Setup-$Version-test.exe")
}
else {
    Write-Output (Join-Path $artifactRoot "Thunderbird-PDF-Archiver-Setup-$Version-win-x64.exe")
}
