# DreamMV v2.0.1 installer
# Windows PowerShell 5.1 compatible. ASCII-only.

param(
    [string]$AppDir = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"
Set-Location $AppDir

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host " DreamMV v2.0.1 Setup" -ForegroundColor Cyan
Write-Host " Animagine XL 4.0 + LTX-2.5" -ForegroundColor Cyan
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

$UvPath = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
if (-not (Test-Path $UvPath)) {
    $UvCommand = Get-Command uv -ErrorAction SilentlyContinue
    if ($UvCommand) {
        $UvPath = $UvCommand.Source
    }
}

if (-not (Test-Path $UvPath)) {
    throw "uv installation failed."
}

& $UvPath --version

Write-Host ""
Write-Host "[1/5] Installing DreamMV dependencies..."

& $UvPath sync --locked --python 3.11 --no-install-project
if ($LASTEXITCODE -ne 0) {
    throw "DreamMV dependency installation failed."
}

$py = Join-Path $AppDir ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    throw "DreamMV Python executable not found: $py"
}

Write-Host ""
Write-Host "[2/5] Verifying DreamMV dependencies..."

& $py -c "import sys, torch, torchvision, diffusers, transformers, accelerate, compel, librosa, soundfile, faster_whisper, PySide6, huggingface_hub, imageio_ffmpeg; print('Python:', sys.version); print('Torch:', torch.__version__); print('Torchvision:', torchvision.__version__); print('CUDA:', torch.cuda.is_available()); assert torch.cuda.is_available(), 'CUDA is not available'; print('DreamMV dependencies: OK')"

if ($LASTEXITCODE -ne 0) {
    throw "DreamMV dependency verification failed."
}

Write-Host ""
Write-Host "[3/5] Downloading Animagine XL 4.0..."

& $py (Join-Path $AppDir "installer\download_model.py")

if ($LASTEXITCODE -ne 0) {
    throw "Animagine model download failed."
}

Write-Host ""
Write-Host "[4/5] Installing LTX-2.5 runtime..."

$LtxInstaller = Join-Path $AppDir "installer\install_ltx25.ps1"

if (-not (Test-Path $LtxInstaller)) {
    throw "LTX-2.5 installer not found: $LtxInstaller"
}

try {
    & $LtxInstaller -AppDir $AppDir
}
catch {
    throw "LTX-2.5 runtime installation failed: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "[5/5] Optional LTX-2.5 model download"

$DownloadChoice = Read-Host "Download approximately 66 GB of LTX-2.5 model files now? (Y/N)"

if ($DownloadChoice -match '^[Yy]$') {
    $LtxRoot = "C:\AI\DreamMV-LTX25\LTX-2"
    $LtxPython = Join-Path $LtxRoot ".venv\Scripts\python.exe"
    $HfExe = Join-Path $LtxRoot ".venv\Scripts\hf.exe"

    $HasToken = & $LtxPython -c "from huggingface_hub import get_token; print('yes' if get_token() else 'no')"

    if ($HasToken -notmatch 'yes') {
        if (-not (Test-Path $HfExe)) {
            throw "Hugging Face CLI was not found. Run hf auth login from the LTX environment."
        }

        Write-Host "Please sign in to Hugging Face."
        & $HfExe auth login

        if ($LASTEXITCODE -ne 0) {
            throw "Hugging Face authentication failed."
        }
    }

    & $LtxPython (Join-Path $AppDir "installer\download_ltx25_models.py")

    if ($LASTEXITCODE -ne 0) {
        throw "LTX-2.5 model download failed."
    }
}
else {
    Write-Host "Skipping LTX-2.5 model download. You can download them later."
}

Write-Host ""
Write-Host "DreamMV setup completed successfully." -ForegroundColor Green
Read-Host "Press Enter to close"
