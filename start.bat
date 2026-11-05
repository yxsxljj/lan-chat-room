@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PY="
if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"
if not defined PY if exist "%~dp0..\.venv\Scripts\python.exe" set "PY=%~dp0..\.venv\Scripts\python.exe"

if not defined PY (
  echo No virtual environment found.
  echo.
  echo Create one first:
  echo   uv venv --python 3.11
  echo   uv pip install -r requirements.txt
  echo.
  pause
  exit /b 1
)

"%PY%" main.py
pause
