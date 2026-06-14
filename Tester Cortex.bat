@echo off
cd /d "%~dp0"
set PYTHONDONTWRITEBYTECODE=1
".venv\Scripts\python.exe" -m unittest discover -s tests -v
".venv\Scripts\python.exe" -m pip check
pause
