param(
    [string]$AppName = "ReservationApp",
    [string]$EntryPoint = "7Jan.py"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $EntryPoint)) {
    throw "Entry point '$EntryPoint' was not found."
}

$pyinstaller = python -m PyInstaller --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller not found. Installing..."
    python -m pip install pyinstaller
}

Write-Host "Building $AppName from $EntryPoint..."
python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name $AppName `
    $EntryPoint

Write-Host "Build complete. EXE output: dist\\$AppName.exe"
