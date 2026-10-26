# DreamMV セットアップ: Python環境 + PyTorch(CUDA) + Wan重みのダウンロード
param([string]$AppDir = (Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference = "Stop"
Set-Location $AppDir

Write-Host "=== DreamMV セットアップ ===" -ForegroundColor Cyan
if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
    Write-Host "NVIDIA GPU / ドライバが見つかりません。Wanの生成にはNVIDIA GPUが必要です。" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "モデルを選んでください:"
Write-Host "  1) light    Wan2.1 1.3B  (480p, VRAM 8GB〜)"
Write-Host "  2) standard Wan2.2 5B    (720p, VRAM 16GB〜, ディスク数十GB)"
$choice = Read-Host "番号 [1]"
$preset = if ($choice -eq "2") { "standard" } else { "light" }

# uv (Python自体も取得してくれる)
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv をインストール中..."
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

uv venv .venv --python 3.11
$py = Join-Path $AppDir ".venv\Scripts\python.exe"

Write-Host "PyTorch (CUDA 12.8) をインストール中..."
uv pip install --python $py torch torchvision --index-url https://download.pytorch.org/whl/cu128

Write-Host "依存ライブラリをインストール中..."
uv pip install --python $py "diffusers>=0.35" transformers accelerate sentencepiece ftfy `
    "imageio[ffmpeg]" imageio-ffmpeg huggingface_hub PySide6
if (Test-Path "$AppDir\requirements.txt") {
    uv pip install --python $py -r "$AppDir\requirements.txt"
}

$repos = @{ light = "Wan-AI/Wan2.1-T2V-1.3B-Diffusers"; standard = "Wan-AI/Wan2.2-TI2V-5B-Diffusers" }
$models = Join-Path $AppDir "models"
Write-Host "Wan重みをダウンロード中 ($($repos[$preset])) ... 時間がかかります"
& $py -c "from huggingface_hub import snapshot_download; snapshot_download('$($repos[$preset])', cache_dir=r'$models')"

@{ preset = $preset; models_dir = $models } | ConvertTo-Json | Set-Content (Join-Path $AppDir "wan_settings.json")
Write-Host "完了しました。" -ForegroundColor Green
Read-Host "Enterで閉じる"
