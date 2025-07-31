@echo off
REM TechGuides Protocol Handler
REM Thecho Launching Python script: %tool%
set "py_path=C:\Tools\Scripts\Tech Guides Website\client_tools\%tool%.py"

if exist "%py_path%" (
    echo Starting %py_path%
    start "" python "%py_path%"
) else (
    echo Python script not found: %py_path%
    echo Error: Neither EXE nor Python script found for tool: %tool%
    pause
)e handles techguides:// protocol launches
REM It supports both EXE and Python script launching

REM Parse the URL to extract parameters
set "url=%~1"
echo Received URL: %url%

REM Remove techguides:// prefix
set "params=%url:techguides://=%"
echo Parameters: %params%

REM Check what action is requested
echo %params% | findstr "launch-exe" >nul
if %errorlevel%==0 goto :LAUNCH_EXE

echo %params% | findstr "launch-python" >nul
if %errorlevel%==0 goto :LAUNCH_PYTHON

echo %params% | findstr "launch" >nul
if %errorlevel%==0 goto :LAUNCH_AUTO

goto :UNKNOWN

:LAUNCH_EXE
REM Extract tool name from URL parameters
for /f "tokens=2 delims==" %%a in ('echo %params% ^| findstr "tool="') do set "tool=%%a"
REM Remove any additional parameters after &
for /f "tokens=1 delims=&" %%b in ('echo %tool%') do set "tool=%%b"

echo Launching EXE: %tool%
set "exe_path=C:\Tools\Scripts\Tech Guides Website\client_tools\%tool%.exe"

if exist "%exe_path%" (
    echo Starting %exe_path%
    start "" "%exe_path%"
) else (
    echo EXE not found: %exe_path%
    echo Trying Python fallback...
    goto :LAUNCH_PYTHON_FALLBACK
)
goto :END

:LAUNCH_PYTHON
REM Extract tool name from URL parameters
for /f "tokens=2 delims==" %%a in ('echo %params% ^| findstr "tool="') do set "tool=%%a"
REM Remove any additional parameters after &
for /f "tokens=1 delims=&" %%b in ('echo %tool%') do set "tool=%%b"

:LAUNCH_PYTHON_FALLBACK
echo Launching Python script: %tool%
set "py_path=C:\Tools\Scripts\Tech Guides Website\client_tools\%tool%.py"

if exist "%py_path%" (
    echo Starting %py_path%
    start "" python "%py_path%"
) else (
    echo Python script not found: %py_path%
    echo Error: Neither EXE nor Python script found for tool: %tool%
    pause
)
goto :END

:LAUNCH_AUTO
REM Extract tool name from URL parameters
for /f "tokens=2 delims==" %%a in ('echo %params% ^| findstr "tool="') do set "tool=%%a"
REM Remove any additional parameters after &
for /f "tokens=1 delims=&" %%b in ('echo %tool%') do set "tool=%%b"

echo Auto-launching tool: %tool%

REM Try EXE first, then Python
set "exe_path=C:\Tools\Scripts\Tech Guides Website\client_tools\%tool%.exe"
set "py_path=C:\Tools\Scripts\Tech Guides Website\client_tools\%tool%.py"

if exist "%exe_path%" (
    echo Found EXE, starting %exe_path%
    start "" "%exe_path%"
) else if exist "%py_path%" (
    echo EXE not found, trying Python script %py_path%
    start "" python "%py_path%"
) else (
    echo Error: Neither EXE nor Python script found for tool: %tool%
    echo Checked:
    echo   %exe_path%
    echo   %py_path%
    pause
)
goto :END

:UNKNOWN
echo Unknown protocol action: %params%
echo Supported formats:
echo   techguides://launch?tool=TOOLNAME
echo   techguides://launch-exe?tool=TOOLNAME
echo   techguides://launch-python?tool=TOOLNAME
pause

:END
echo Protocol handler finished.
REM Don't pause on successful launches to avoid blocking
