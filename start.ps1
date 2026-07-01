# gex-sample-cloud — one-command local run.
# Creates a virtualenv, installs deps, starts the app, opens the dashboard.
# Stays open and shows the error if anything fails (never silently exits).
$ErrorActionPreference = "Stop"
try {
    Set-Location $PSScriptRoot

    if (-not (Test-Path ".venv")) {
        Write-Host "Creating virtualenv (.venv)..."
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Could not create virtualenv. Is Python installed and on PATH?" }
    }
    $py = ".\.venv\Scripts\python.exe"

    Write-Host "Installing dependencies..."
    & $py -m pip install --disable-pip-version-check -q -r requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { throw "pip install failed (exit $LASTEXITCODE)." }

    $env:PORT = "8080"
    Write-Host ""
    Write-Host "GEX sample running at http://127.0.0.1:8080   (press Ctrl+C to stop)" -ForegroundColor Green
    Write-Host ""
    Start-Job -ScriptBlock { Start-Sleep 3; Start-Process "http://127.0.0.1:8080" } | Out-Null

    & $py run.py
    if ($LASTEXITCODE -ne 0) { throw "The app exited with code $LASTEXITCODE (see the error above)." }
}
catch {
    Write-Host ""
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "Press Enter to close"
}
