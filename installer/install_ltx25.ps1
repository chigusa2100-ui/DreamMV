
# DreamMV LTX-2.5 runtime installer
# Windows PowerShell 5.1 compatible.

param(
    [string]$AppDir = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"

$LtxParent = "C:\AI\DreamMV-LTX25"
$LtxRoot = Join-Path $LtxParent "LTX-2"
$ModelRoot = Join-Path $LtxParent "models"

$AssetDir = Join-Path $AppDir "installer\ltx25"
$Patch = Join-Path $AssetDir "patches\windows-runtime.patch"
$LockSource = Join-Path $AssetDir "uv.lock"
$CommitFile = Join-Path $AssetDir "UPSTREAM_COMMIT.txt"

$TempDir = Join-Path $env:TEMP "DreamMV-LTX25-Install"
$SourceDir = Join-Path $TempDir "LTX-2"
$Repository = "https://github.com/Lightricks/LTX-2.git"

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host " DreamMV LTX-2.5 Runtime Setup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# Installer assets
foreach ($file in @($Patch, $LockSource, $CommitFile)) {
    if (-not (Test-Path $file -PathType Leaf)) {
        throw "Required installer asset is missing: $file"
    }
}

$Commit = (Get-Content $CommitFile -Raw).Trim()

if ($Commit -notmatch '^[0-9a-f]{40}$') {
    throw "Invalid upstream commit: $Commit"
}

# Git
$Git = Get-Command git -ErrorAction SilentlyContinue

if (-not $Git) {
    throw "Git for Windows is required. Install Git and run this installer again."
}

$GitPath = $Git.Source
if (-not $GitPath) {
    $GitPath = $Git.FullName
}

# uv
$Uv = Get-Command uv -ErrorAction SilentlyContinue

if (-not $Uv) {
    $UvPath = Join-Path $env:USERPROFILE ".local\bin\uv.exe"

    if (Test-Path $UvPath) {
        $Uv = Get-Item $UvPath
    }
}

if (-not $Uv) {
    throw "uv was not found. Run the main DreamMV installer first."
}

$UvPath = $Uv.Source
if (-not $UvPath) {
    $UvPath = $Uv.FullName
}

New-Item -ItemType Directory -Path $LtxParent -Force | Out-Null
New-Item -ItemType Directory -Path $ModelRoot -Force | Out-Null

$SourceReady = $false

# Reuse existing source when possible
if (Test-Path $LtxRoot -PathType Container) {
    Write-Host "[1/4] Checking existing LTX source..."

    $GitDir = Join-Path $LtxRoot ".git"

    if (Test-Path $GitDir) {
        $ExistingCommit = (& $GitPath -C $LtxRoot rev-parse HEAD).Trim()

        if ($LASTEXITCODE -ne 0 -or $ExistingCommit -ne $Commit) {
            throw "Existing LTX source has a different commit. Refusing to overwrite: $LtxRoot"
        }

        Write-Host "Existing pinned source detected."

        & $GitPath -C $LtxRoot apply --reverse --check $Patch 2>$null

        if ($LASTEXITCODE -ne 0) {
            & $GitPath -C $LtxRoot apply --check $Patch

            if ($LASTEXITCODE -ne 0) {
                throw "The Windows runtime patch cannot be applied to the existing source."
            }

            & $GitPath -C $LtxRoot apply $Patch

            if ($LASTEXITCODE -ne 0) {
                throw "Failed to apply the Windows runtime patch."
            }
        }
        else {
            Write-Host "Windows runtime patch is already applied."
        }

        $SourceReady = $true
    }
    else {
        throw "The LTX destination exists but is not a Git repository. Refusing to overwrite it: $LtxRoot"
    }
}

# Clone pinned source into a temporary directory
if (-not $SourceReady) {
    Write-Host "[1/4] Cloning LTX-2.5 source from GitHub..."

    if (Test-Path $TempDir) {
        Remove-Item $TempDir -Recurse -Force
    }

    New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

    & $GitPath clone --filter=blob:none --no-checkout $Repository $SourceDir

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to clone the LTX repository."
    }

    Write-Host "[2/4] Fetching pinned upstream commit..."

    & $GitPath -C $SourceDir fetch --depth 1 origin $Commit

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to fetch pinned LTX commit: $Commit"
    }

    & $GitPath -C $SourceDir checkout --detach $Commit

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to checkout pinned LTX commit."
    }

    $CheckedOutCommit = (& $GitPath -C $SourceDir rev-parse HEAD).Trim()

    if ($LASTEXITCODE -ne 0 -or $CheckedOutCommit -ne $Commit) {
        throw "Checked out LTX commit does not match the pinned commit."
    }

    Write-Host "[3/4] Applying Windows runtime patch..."

    & $GitPath -C $SourceDir apply --check $Patch

    if ($LASTEXITCODE -ne 0) {
        throw "LTX Windows patch validation failed."
    }

    & $GitPath -C $SourceDir apply $Patch

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to apply LTX Windows runtime patch."
    }

    Copy-Item $LockSource (Join-Path $SourceDir "uv.lock") -Force

    $Metadata = @{
        commit = $Commit
        patch_applied = $true
        model_repository = "Lightricks/LTX-2.5"
    } | ConvertTo-Json

    Set-Content `
        -Path (Join-Path $SourceDir ".dreammv-install.json") `
        -Value $Metadata `
        -Encoding UTF8

    if (Test-Path $LtxRoot) {
        throw "LTX destination appeared during installation. Refusing to overwrite."
    }

    Move-Item -Path $SourceDir -Destination $LtxRoot

    Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "[3/4] Preparing Python 3.12 environment..."

Copy-Item $LockSource (Join-Path $LtxRoot "uv.lock") -Force

Push-Location $LtxRoot

try {
    & $UvPath sync --frozen --python 3.12

    if ($LASTEXITCODE -ne 0) {
        throw "LTX dependency installation failed."
    }
}
finally {
    Pop-Location
}

$LtxPython = Join-Path $LtxRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $LtxPython)) {
    throw "LTX Python environment was not created: $LtxPython"
}

Write-Host "[4/4] Verifying LTX runtime..."

& $LtxPython -c "import sys, torch, torchvision, transformers; import ltx_pipelines; print('Python:', sys.version); print('Torch:', torch.__version__); print('Torchvision:', torchvision.__version__); print('Transformers:', transformers.__version__); print('CUDA:', torch.cuda.is_available()); assert torch.cuda.is_available(), 'CUDA is not available'; print('LTX Python packages: OK')"

if ($LASTEXITCODE -ne 0) {
    throw "LTX runtime verification failed."
}

$VerifyCode = "import subprocess,sys; r=subprocess.run([sys.executable, '-X', 'utf8', '-m', 'ltx_pipelines.distilled', '--help'],capture_output=True,text=True,encoding='utf-8',errors='replace'); print('LTX CLI verification: OK') if r.returncode == 0 else sys.exit(r.returncode)"
$VerifyCode | & $LtxPython -X utf8 -

if ($LASTEXITCODE -ne 0) {
    throw "LTX CLI verification failed."
}

Write-Host ""
Write-Host "LTX-2.5 runtime installed successfully." -ForegroundColor Green
Write-Host "Source: $LtxRoot"
Write-Host "Models: $ModelRoot"
Write-Host "Python: $LtxPython"
