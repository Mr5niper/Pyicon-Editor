@echo off
setlocal enabledelayedexpansion

:: ============================================================================
::  Pyicon-Editor  --  EXE Builder
::  Strictly requires Python 3.13.12
::  Works even when Python is NOT on PATH (uses the "py" launcher).
:: ============================================================================

set "REQUIRED_VERSION=3.13.12"
set "DOWNLOAD_URL=https://www.python.org/downloads/release/python-31312/"

echo Checking Python version...

:: --- Find an interpreter that is EXACTLY 3.13.12 --------------------------
:: Prefer the "py" launcher pinned to 3.13, then fall back to "python" on PATH.
set "PY_CMD="
set "VER_A="
set "VER_B="

for /f "tokens=2" %%I in ('py -3.13 --version 2^>nul') do set "VER_A=%%I"
if "!VER_A!"=="%REQUIRED_VERSION%" set "PY_CMD=py -3.13"

if not defined PY_CMD (
    for /f "tokens=2" %%I in ('python --version 2^>nul') do set "VER_B=%%I"
    if "!VER_B!"=="%REQUIRED_VERSION%" set "PY_CMD=python"
)

if not defined PY_CMD (
    set "CURRENT_VERSION=!VER_B!"
    if not defined CURRENT_VERSION set "CURRENT_VERSION=!VER_A!"
    if not defined CURRENT_VERSION set "CURRENT_VERSION=None"
    if "!CURRENT_VERSION!"=="" set "CURRENT_VERSION=None"
    goto :WrongVersion
)

echo Python %REQUIRED_VERSION% detected via "!PY_CMD!". Proceeding with setup...
echo =======================================================

:: 1. Create Virtual Environment
echo [1/6] Creating virtual environment...
%PY_CMD% -m venv .venv
if %ERRORLEVEL% NEQ 0 ( echo ERROR: venv creation failed. & goto :End )

:: 2. Activate Virtual Environment (Using .bat instead of .ps1 for Batch scripts)
echo [2/6] Activating virtual environment...
call ".venv\Scripts\activate.bat"
if %ERRORLEVEL% NEQ 0 ( echo ERROR: could not activate venv. & goto :End )

:: 3. Upgrade build tools
echo [3/6] Upgrading pip, setuptools, and wheel...
python -m pip install --upgrade pip setuptools wheel

:: 4. Install Requirements
echo [4/6] Installing dependencies from requirements.txt...
if exist requirements.txt (
    python -m pip install -r requirements.txt
) else (
    echo WARNING: requirements.txt not found. Skipping...
)

:: 5. Install PyInstaller
echo [5/6] Installing PyInstaller...
python -m pip install pyinstaller
if %ERRORLEVEL% NEQ 0 ( echo ERROR: PyInstaller install failed. & goto :End )

:: 6. Run PyInstaller
echo [6/6] Building executable...
if exist icon_editor.spec (
    pyinstaller --clean --noconfirm icon_editor.spec
    if %ERRORLEVEL% NEQ 0 (
        echo =======================================================
        echo ERROR: Build failed. Scroll up for the PyInstaller error.
        goto :End
    )
    echo =======================================================
    echo Build completed successfully!
) else (
    echo ERROR: icon_editor.spec not found!
)

goto :End

:WrongVersion
echo =======================================================
echo ERROR: Incorrect Python Version!
echo.
echo You currently have: Python !CURRENT_VERSION!
echo This script requires exactly: Python %REQUIRED_VERSION%
echo.
echo Please download and install Python %REQUIRED_VERSION% from here:
echo %DOWNLOAD_URL%
echo.
echo Make sure to check the box "Add Python to PATH" during installation.
echo =======================================================
start "" "%DOWNLOAD_URL%"

:End
echo Press any key to exit...
pause >nul
exit /b