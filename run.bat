@echo off
cd /d %~dp0
if not exist ".venv\Scripts\python.exe" (
  echo .venv was not found. Run installer\install.ps1 first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" DreamMV.py
if errorlevel 1 pause