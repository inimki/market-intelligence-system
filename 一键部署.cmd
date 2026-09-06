@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\deploy.ps1"
if errorlevel 1 (
  echo Deployment failed. See the error above and open the README or TXT guide.
  pause
  exit /b 1
)
pause
