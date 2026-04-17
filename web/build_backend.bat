@echo off
setlocal

REM Build Flask backend exe into web/dist/backend
cd /d "%~dp0"

if not exist ".venv" (
  echo [WARN] web\.venv not found. Please ensure Python deps installed.
)

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

if exist "dist\backend" rmdir /s /q "dist\backend"
if exist "build" rmdir /s /q "build"

REM NOTE:
REM python-socketio / python-engineio load async drivers dynamically.
REM When frozen with PyInstaller, these submodules may be missed unless explicitly collected,
REM leading to: ValueError: Invalid async_mode specified

python -m PyInstaller --noconfirm --clean --name fire-alarm-web --onefile app.py ^
  --distpath "dist\backend" ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --collect-submodules "engineio.async_drivers" ^
  --collect-submodules "socketio.async_drivers"

echo Backend build complete: web\dist\backend\fire-alarm-web.exe
endlocal
