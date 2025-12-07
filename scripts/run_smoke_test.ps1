param(
    [int] $AutoCloseMs = 5000
)

$ErrorActionPreference = 'Stop'

function Resolve-Python {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return (Get-Command python).Source
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return (Get-Command py).Source
    }
    $candidates = @(
        "$env:LocalAppData\Programs\Python",
        'C:\\Python',
        'C:\\Program Files',
        'C:\\Program Files (x86)'
    )
    foreach ($root in $candidates) {
        if (Test-Path $root) {
            $hits = Get-ChildItem -Path $root -Recurse -Filter python.exe -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($hits) { return $hits.FullName }
        }
    }
    throw 'Python executable not found. Ensure Python is installed and added to PATH.'
}

Write-Host '==> Resolving Python...'
$python = Resolve-Python
& $python -V

$repoRoot = Split-Path $PSScriptRoot -Parent
$venvDir = Join-Path $repoRoot '.venv'
$venvPy  = Join-Path $venvDir 'Scripts\python.exe'

if (-not (Test-Path $venvDir)) {
    Write-Host '==> Creating virtual environment (.venv)...'
    & $python -m venv $venvDir
}

Write-Host '==> Upgrading pip...'
& $venvPy -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { Write-Warning 'pip upgrade failed, continuing...' }

Write-Host '==> Installing PyTorch CPU wheels (torch, torchvision, torchaudio)...'
& $venvPy -m pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio -U
if ($LASTEXITCODE -ne 0) {
    Write-Warning 'Stable CPU wheels failed. Trying nightly CPU wheels...'
    & $venvPy -m pip install --pre --index-url https://download.pytorch.org/whl/nightly/cpu torch torchvision torchaudio -U
    if ($LASTEXITCODE -ne 0) { Write-Warning 'Nightly CPU wheels also failed. Proceeding without PyTorch.' }
}

Write-Host '==> Installing remaining dependencies (batch)...'
& $venvPy -m pip install opencv-python pyqt5 pyqtwebengine selenium webdriver-manager requests -U
if ($LASTEXITCODE -ne 0) {
    Write-Warning 'Batch install failed. Retrying critical packages individually...'
    & $venvPy -m pip install pyqt5 -U; if ($LASTEXITCODE -ne 0) { Write-Warning 'pyqt5 install failed.' }
    & $venvPy -m pip install pyqtwebengine -U; if ($LASTEXITCODE -ne 0) { Write-Warning 'pyqtwebengine install failed.' }
    & $venvPy -m pip install selenium webdriver-manager requests -U; if ($LASTEXITCODE -ne 0) { Write-Warning 'selenium/webdriver-manager/requests install failed.' }
    # opencv is optional for this smoke test; skip if it fails
}

Write-Host '==> Warming up model (downloads weights on first run)...'
$pycode = @"
import sys
import numpy as np
try:
    from models.ai_model import AIModel
    m = AIModel()
    print(m.predict(np.zeros((224,224,3), dtype=np.uint8)))
except Exception as e:
    print('Warm-up skipped:', e)
    sys.exit(0)
"@
$pycode | & $venvPy -
if ($LASTEXITCODE -ne 0) { Write-Warning 'Warm-up failed or skipped.' }

Write-Host "==> Launching GUI (auto-close ${AutoCloseMs} ms)..."
& $venvPy (Join-Path $repoRoot 'main.py') --auto-close-ms $AutoCloseMs

Write-Host '==> Smoke test complete.'
