@echo off
setlocal
set "VENV_DIR=venv"

set "PY=%~dp0%VENV_DIR%\Scripts\python.exe"
if not exist "%PY%" (
    echo Creating virtual environment...
    python -m venv "%VENV_DIR%"
    "%PY%" -m pip install -r requirements.txt
)

call "%~dp0start_comfy.bat"

echo Starting AetherCanvas AI on http://127.0.0.1:7870
"%PY%" app.py
pause
