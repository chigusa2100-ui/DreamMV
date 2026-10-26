# DreamMV setup: Python env + PyTorch (CUDA) + Wan weights
# NOTE: this file is intentionally ASCII-only (Windows PowerShell 5.1 reads BOM-less files as Shift-JIS)
param([string]$AppDir = (Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference = "Stop"
Set-Location $AppDir

Write-Host "=== DreamMV setup ===" -ForegroundColor Cyan
if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
    Write-Host "WARNING: nvidia-smi not found. Wan needs an NVIDIA GPU and driver." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Choose a model:"
Write-Host "  1) light    Wan2.1 1.3B  (480p, VRAM 8GB or more)"
Write-Host "  2) standard Wan2.2 5B    (720p, VRAM 16GB or more, tens of GB of disk)"
Write-Host "  3) anime    Animagine XL 4.0 still + camera move (lightest, VRAM 8GB or more, ~7GB disk)"
$choice = Read-Host "Number [1]"
if ($choice -eq "2") { $preset = "standard" } elseif ($choice -eq "3") { $preset = "anime" } else { $preset = "light" }

# uv (also fetches Python itself)
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..."
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

uv venv .venv --python 3.11
$py = Join-Path $AppDir ".venv\Scripts\python.exe"

Write-Host "Installing PyTorch (CUDA 12.8)..."
uv pip install --python $py torch torchvision --index-url https://download.pytorch.org/whl/cu128

Write-Host "Installing dependencies..."
uv pip install --python $py "diffusers>=0.35" transformers accelerate sentencepiece ftfy "imageio[ffmpeg]" imageio-ffmpeg huggingface_hub PySide6 librosa soundfile numpy
if (Test-Path "$AppDir\requirements.txt") {
    uv pip install --python $py -r "$AppDir\requirements.txt"
}

& $py "$AppDir\installer\download_model.py" $preset

Write-Host "Done." -ForegroundColor Green
Read-Host "Press Enter to close"
