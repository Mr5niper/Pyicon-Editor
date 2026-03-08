@echo off
setlocal enabledelayedexpansion

:: Define the required version and download URL
set REQUIRED_VERSION=3.13.12
set DOWNLOAD_URL=https://www.python.org/downloads/release/python-31312/

echo Checking Python version...

:: Check if Python is installed and in PATH
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    set CURRENT_VERSION=None
    goto :WrongVersion
)

:: Get the exact Python version
for /f "tokens=2" %%I in ('python --version') do set CURRENT_VERSION=%%I

:: Compare the installed version to the required version
if "%CURRENT_VERSION%" NEQ "%REQUIRED_VERSION%" (
    goto :WrongVersion
)

echo Python %REQUIRED_VERSION% detected! Proceeding with setup...
echo =======================================================

:: 1. Create Virtual Environment
echo [1/6] Creating virtual environment...
python -m venv .venv

:: 2. Activate Virtual Environment (Using .bat instead of .ps1 for Batch scripts)
echo [2/6] Activating virtual environment...
call .venv\Scripts\activate.bat

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

:: 6. Run PyInstaller
echo [6/6] Building executable...
if exist icon_editor.spec (
    pyinstaller --clean --noconfirm icon_editor.spec
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
echo You currently have: Python %CURRENT_VERSION%
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