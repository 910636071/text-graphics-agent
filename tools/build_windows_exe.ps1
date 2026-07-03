$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "python was not found on PATH"
}

if (-not (Test-Path ".venv-build")) {
    python -m venv .venv-build
}

.\.venv-build\Scripts\python.exe -m pip install --upgrade pip pyinstaller

.\.venv-build\Scripts\python.exe -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name TextGraphicsAgent `
    --collect-submodules text_graphics_agent `
    .\run_gui.py

Write-Host "Built: $Root\dist\TextGraphicsAgent\TextGraphicsAgent.exe"
