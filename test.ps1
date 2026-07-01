# Run the functional test suite in an isolated virtualenv.
# Stays open so you can read results / errors.
$ErrorActionPreference = "Stop"
try {
    Set-Location $PSScriptRoot
    if (-not (Test-Path ".venv")) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Could not create virtualenv. Is Python installed and on PATH?" }
    }
    $py = ".\.venv\Scripts\python.exe"
    & $py -m pip install --disable-pip-version-check -q -r requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { throw "pip install failed (exit $LASTEXITCODE)." }
    & $py -m pytest
}
catch {
    Write-Host ""
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
}
finally {
    Read-Host "`nPress Enter to close"
}
