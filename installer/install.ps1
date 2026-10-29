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
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

uv venv .venv --python 3.11
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create the Python virtual environment."
}

$py = Join-Path $AppDir ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    throw "Python executable not found: $py"
}

Write-Host "Installing PyTorch (CUDA 12.8)..."
uv pip install --python $py torch torchvision --index-url https://download.pytorch.org/whl/cu128
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install PyTorch."
}

Write-Host "Installing DreamMV and Animagine dependencies..."
uv pip install --python $py "diffusers>=0.35" transformers accelerate sentencepiece ftfy "imageio[ffmpeg]" imageio-ffmpeg huggingface_hub PySide6 librosa soundfile numpy pillow faster-whisper "compel==2.5.1"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install DreamMV dependencies."
}

if (Test-Path (Join-Path $AppDir "requirements.txt")) {
    uv pip install --python $py -r (Join-Path $AppDir "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install requirements.txt dependencies."
    }
}

Write-Host "Verifying Whisper dependency..."
& $py -c "from faster_whisper import WhisperModel; print('faster-whisper import OK')"
if ($LASTEXITCODE -ne 0) {
    throw "faster-whisper verification failed."
}

Write-Host "Downloading Animagine XL 4.0..."
& $py (Join-Path $AppDir "installer\download_model.py")
if ($LASTEXITCODE -ne 0) {
    throw "Animagine model setup failed."
}

Write-Host "DreamMV setup completed successfully." -ForegroundColor Green
Read-Host "Press Enter to close"