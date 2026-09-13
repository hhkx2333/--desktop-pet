@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if not errorlevel 1 (
  py -3 -m pip install -r requirements.txt
  if errorlevel 1 goto :failed
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create-desktop-shortcut.ps1"
  call start-erii.cmd
  exit /b 0
)

where python >nul 2>&1
if not errorlevel 1 (
  python -m pip install -r requirements.txt
  if errorlevel 1 goto :failed
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create-desktop-shortcut.ps1"
  call start-erii.cmd
  exit /b 0
)

echo Python 3 was not found. Install it from https://www.python.org/downloads/windows/
echo Make sure "Add Python to PATH" is selected during installation.
pause
exit /b 1

:failed
echo Failed to install dependencies. Check your network connection and try again.
pause
exit /b 1
