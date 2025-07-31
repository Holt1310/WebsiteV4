@echo off
REM TechGuides Client Service - Silent Startup
REM This script starts the service minimized to system tray

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0

REM Start the service hidden (no console window)
start /min "" python "%SCRIPT_DIR%techguides_client_service.py"

REM Alternative if python is not in PATH
REM start /min "" py "%SCRIPT_DIR%techguides_client_service.py"
