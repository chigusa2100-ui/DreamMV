# DreamMV setup launcher
# Keep this file ASCII-only for Windows PowerShell 5.1.
$ErrorActionPreference = "Stop"
$AppDir = $PSScriptRoot
$Installer = Join-Path $AppDir "installer\install.ps1"

if (-not (Test-Path $Installer)) {
    throw "Installer not found: $Installer"
}

& $Installer -AppDir $AppDir
