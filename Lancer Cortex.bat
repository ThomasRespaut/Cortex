@echo off
cd /d "%~dp0"
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
set PYTHONDONTWRITEBYTECODE=1
start "" ".venv\Scripts\pythonw.exe" Screen.py
exit /b 0
