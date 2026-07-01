@echo off
REM Double-click to launch the GEX sample locally and open the dashboard.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
if errorlevel 1 pause
