@echo off
setlocal
cd /d "%~dp0"
title VRPTW Research Launcher

set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo Python 3 was not found.
    echo Install Python 3.10 or newer from https://www.python.org/downloads/ and enable "Add Python to PATH".
    pause
    exit /b 1
)

echo Checking Python version...
%PYTHON_CMD% -c "import sys; print('Python', sys.version.split()[0]); sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo Python 3.10 or newer is required.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating the project environment...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto setup_failed
)

".venv\Scripts\python.exe" -c "import ortools, pandas, matplotlib" >nul 2>nul
if errorlevel 1 (
    echo Installing required packages. This may take a few minutes on first run...
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
    if errorlevel 1 goto setup_failed
)

echo Starting VRPTW launcher...
".venv\Scripts\python.exe" src\launcher.py
if errorlevel 1 (
    echo Launcher exited with an error.
    pause
)
endlocal
exit /b

:setup_failed
echo Setup could not complete. Check your internet connection and Python installation, then run this file again.
pause
endlocal
exit /b 1
