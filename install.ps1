# DreamMV v1.2.0 GitHub installer
# Windows PowerShell 5.1 compatible. ASCII-only.

$ErrorActionPreference = "Stop"

$AppDir = $PSScriptRoot
$Version = "v1.2.0"
$Repo = "chigusa2100-ui/DreamMV"
$ZipUrl = "https://github.com/$Repo/archive/refs/tags/$Version.zip"

$TempDir = Join-Path $env:TEMP "DreamMV-Install-$Version"
$ZipPath = Join-Path $TempDir "DreamMV.zip"
$ExtractDir = Join-Path $TempDir "source"

Write-Host ""
Write-Host "DreamMV $Version GitHub Installer" -ForegroundColor Cyan

try {
    Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path $ExtractDir -Force | Out-Null

    Write-Host "[1/4] Downloading source from GitHub..."
    Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipPath -UseBasicParsing

    Write-Host "[2/4] Extracting source..."
    Expand-Archive -Path $ZipPath -DestinationPath $ExtractDir -Force

    $SourceDir = Get-ChildItem $ExtractDir -Directory | Select-Object -First 1

    if (-not $SourceDir) {
        throw "GitHub source archive is empty."
    }

    if (-not (Test-Path (Join-Path $SourceDir.FullName "DreamMV.py"))) {
        throw "DreamMV.py was not found."
    }

    Write-Host "[3/4] Updating application source..."

    robocopy $SourceDir.FullName $AppDir /E /R:2 /W:2 /XD ".venv" "models" "output" ".git" ".dreammv" "projects" "__pycache__"

    if ($LASTEXITCODE -ge 8) {
        throw "Source copy failed. Robocopy exit code: $LASTEXITCODE"
    }

    Write-Host "[4/4] Starting dependency installer..."

    $Installer = Join-Path $AppDir "installer\install.ps1"

    if (-not (Test-Path $Installer)) {
        throw "Installer not found: $Installer"
    }

    & $Installer -AppDir $AppDir
}
finally {
    Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue
}
