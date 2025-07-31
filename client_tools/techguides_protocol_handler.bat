@echo off
REM TechGuides Protocol Handler
REM This batch file handles techguides:// protocol URLs
REM Usage: techguides_protocol_handler.bat "techguides://launch?tool=chat_overlay&server=http://localhost:5151"

setlocal enabledelayedexpansion

REM Get the URL parameter
set "url=%~1"

REM Remove quotes if present
set "url=!url:"=!"

REM Parse the URL to extract parameters
echo Received URL: %url%

REM Extract tool name
for /f "tokens=2 delims==" %%a in ('echo %url% ^| findstr /i "tool="') do (
    for /f "tokens=1 delims=&" %%b in ("%%a") do set "tool=%%b"
)

REM Extract server URL
for /f "tokens=2 delims==" %%a in ('echo %url% ^| findstr /i "server="') do (
    for /f "tokens=1 delims=&" %%b in ("%%a") do set "server=%%b"
)

echo Tool: %tool%
echo Server: %server%

REM Check if tool exists
set "tool_path=C:\ClientTools\%tool%.py"
if not exist "%tool_path%" (
    echo ERROR: Tool not found at %tool_path%
    echo.
    echo Please ensure the tool is installed at C:\ClientTools\%tool%.py
    pause
    exit /b 1
)

REM Launch the tool
echo Launching %tool%...
echo.

REM Change to ClientTools directory
cd /d "C:\ClientTools"

REM Launch Python with the tool
python "%tool%.py"

if errorlevel 1 (
    echo.
    echo Error launching tool. Please check:
    echo 1. Python is installed and in PATH
    echo 2. Required packages are installed
    echo 3. Tool file exists and is not corrupted
    echo.
    pause
)

exit /b 0
