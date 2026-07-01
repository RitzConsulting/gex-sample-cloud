# gex-sample-cloud — one-command local run.
# Creates a virtualenv, installs deps, starts the app, and opens the dashboard.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtualenv (.venv)..."
    python -m venv .venv
}
$py = ".\.venv\Scripts\python.exe"

Write-Host "Installing dependencies..."
& $py -m pip install --quiet --disable-pip-version-check -r requirements-dev.txt

$env:PORT = "8080"
Write-Host ""
Write-Host "GEX sample running at http://127.0.0.1:8080   (press Ctrl+C to stop)" -ForegroundColor Green
Write-Host ""
# Open the browser a few seconds after the server starts.
Start-Job -ScriptBlock { Start-Sleep 3; Start-Process "http://127.0.0.1:8080" } | Out-Null
& $py run.py
