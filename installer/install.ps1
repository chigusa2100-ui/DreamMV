# DreamMV setup: Python environment + PyTorch CUDA + Animagine XL 4.0
# NOTE: this file is intentionally ASCII-only for Windows PowerShell 5.1.
param([string]$AppDir = (Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference = "Stop"
Set-Location $AppDir

Write-Host "=== DreamMV setup (Animagine XL 4.0) ===" -ForegroundColor Cyan
if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
    Write-Host "WARNING: nvidia-smi not found. An NVIDIA GPU and driver are required." -ForegroundColor Yellow
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..."
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:Path = "$env:USERPROFILE\\.local\\bin;$env:Path"
}

uv venv .venv --python 3.11
$py = Join-Path $AppDir ".venv\\Scripts\\python.exe"

Write-Host "Installing PyTorch (CUDA 12.8)..."
uv pip install --python $py torch torchvision --index-url https://download.pytorch.org/whl/cu128

Write-Host "Installing Animagine dependencies..."
uv pip install --python $py "diffusers>=0.35" transformers accelerate sentencepiece ftfy "imageio[ffmpeg]" imageio-ffmpeg huggingface_hub PySide6 librosa soundfile numpy pillow
if (Test-Path "$AppDir\\requirements.txt") {
    uv pip install --python $py -r "$AppDir\\requirements.txt"
}

& $py "$AppDir\\installer\\download_model.py"

Write-Host "Done." -ForegroundColor Green
Read-Host "Press Enter to close"
