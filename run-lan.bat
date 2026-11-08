@echo off
rem Serve the UI on the whole local network (reachable as http://qwen.flask:7870).
setlocal
set "VENV_DIR=venv"
set "HOST=0.0.0.0"
set "PORT=7870"

set "PY=%~dp0%VENV_DIR%\Scripts\python.exe"
if not exist "%PY%" (
    python -m venv "%VENV_DIR%"
    "%PY%" -m pip install -r requirements.txt
)

call "%~dp0start_comfy.bat"

echo Serving on http://0.0.0.0:%PORT%  (LAN: http://qwen.flask:%PORT%)
"%PY%" app.py
pause
