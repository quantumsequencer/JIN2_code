@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0JINLauncher.ps1"
if errorlevel 1 (
  echo JIN Launcher could not start. Please run JINLauncher.ps1 in PowerShell to see details.
  pause
)
