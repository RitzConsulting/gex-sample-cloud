# Run the functional test suite in an isolated virtualenv.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path ".venv")) { python -m venv .venv }
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --quiet --disable-pip-version-check -r requirements-dev.txt
& $py -m pytest
