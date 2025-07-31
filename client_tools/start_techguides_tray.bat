@echo off
REM TechGuides Client Service Startup Script
REM This script starts the TechGuides client service with system tray support

echo Starting TechGuides Client Service...

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0

REM Change to the client tools directory
cd /d "%SCRIPT_DIR%"

REM Start the client service (using python command - adjust if needed)
python techguides_client_service.py

REM If python command fails, try python3
if errorlevel 1 (
    echo Python command failed, trying python3...
    python3 techguides_client_service.py
)

REM If that fails too, try py launcher
if errorlevel 1 (
    echo Python3 command failed, trying py launcher...
    py techguides_client_service.py
)

REM If all fail, show error
if errorlevel 1 (
    echo Error: Could not start TechGuides Client Service
    echo Please ensure Python is installed and in your PATH
    pause
)
