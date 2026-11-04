# DreamMV v1.1.1 installer
# Windows PowerShell 5.1 compatible. ASCII-only.

param(
    [string]$AppDir = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"
Set-Location $AppDir

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host " DreamMV v1.1.1 Setup" -ForegroundColor Cyan
Write-Host " Animagine XL 4.0" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
    throw "NVIDIA driver was not detected."
}

nvidia-smi

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..."
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv installation failed."
}

uv --version

Write-Host ""
Write-Host "[1/4] Installing locked dependencies..."

uv sync --locked --python 3.11 --no-install-project
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed."
}

$py = Join-Path $AppDir ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    throw "Python executable not found: $py"
}

Write-Host ""
Write-Host "[2/4] Verifying dependencies..."

& $py -c "import sys, torch, torchvision, diffusers, transformers, accelerate, compel, librosa, soundfile, faster_whisper, PySide6, huggingface_hub, imageio_ffmpeg; print('Python:', sys.version); print('Torch:', torch.__version__); print('Torchvision:', torchvision.__version__); print('CUDA:', torch.cuda.is_available()); assert torch.cuda.is_available(), 'CUDA is not available'; print('DreamMV dependencies: OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Dependency verification failed."
}

Write-Host ""
Write-Host "[3/4] Downloading Animagine XL 4.0..."

& $py (Join-Path $AppDir "installer\download_model.py")

if ($LASTEXITCODE -ne 0) {
    throw "Animagine model download failed."
}

Write-Host ""
Write-Host "[4/4] Setup completed."

Write-Host "DreamMV setup completed successfully." -ForegroundColor Green
Read-Host "Press Enter to close"
