@echo off
REM TechGuides Client Service Launcher
REM This batch file provides an easy way to start the TechGuides Client Service

echo ========================================
echo    TechGuides Client Service Launcher
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.7 or later from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo Python is installed: 
python --version

echo.
echo Checking for required packages...

REM Check if required packages are installed
python -c "import tkinter, requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing required packages...
    pip install requests
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install required packages
        echo Please run: pip install requests
        pause
        exit /b 1
    )
)

echo Required packages are available.
echo.
echo Starting TechGuides Client Service...
echo.

REM Start the host service
python app.py

echo.
echo Client service has been stopped.
pause
