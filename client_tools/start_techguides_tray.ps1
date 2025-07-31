# TechGuides Client Service Startup Script (PowerShell)
# This script starts the TechGuides client service silently with system tray support

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Change to the client tools directory
Set-Location $ScriptDir

# Try to start the client service
try {
    Write-Host "Starting TechGuides Client Service..." -ForegroundColor Green
    
    # First try python
    if (Get-Command python -ErrorAction SilentlyContinue) {
        python techguides_client_service.py
    }
    # If python fails, try python3
    elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
        python3 techguides_client_service.py
    }
    # If that fails, try py launcher
    elseif (Get-Command py -ErrorAction SilentlyContinue) {
        py techguides_client_service.py
    }
    else {
        throw "No Python interpreter found"
    }
}
catch {
    Write-Error "Error starting TechGuides Client Service: $_"
    Write-Host "Please ensure Python is installed and in your PATH" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
}
