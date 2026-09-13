@echo off
setlocal
cd /d "%~dp0"

where pyw >nul 2>&1
if not errorlevel 1 (
  start "绘梨衣" pyw -3 "%~dp0desktop_pet.py"
  exit /b 0
)

where pythonw >nul 2>&1
if not errorlevel 1 (
  start "绘梨衣" pythonw "%~dp0desktop_pet.py"
  exit /b 0
)

echo Python 3 was not found. Install it from https://www.python.org/downloads/windows/
echo Make sure "Add Python to PATH" is selected during installation.
pause
exit /b 1
