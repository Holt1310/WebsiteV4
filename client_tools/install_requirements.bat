@echo off
echo TechGuides Client Setup - Quick Fix
echo ===================================
echo.
echo Installing required Python packages...
echo.

pip install selenium
if %errorlevel% neq 0 (
    echo Error installing selenium
    pause
    exit /b 1
)

pip install requests
if %errorlevel% neq 0 (
    echo Error installing requests
    pause
    exit /b 1
)

pip install pillow
if %errorlevel% neq 0 (
    echo Error installing pillow
    pause
    exit /b 1
)

pip install pystray
if %errorlevel% neq 0 (
    echo Error installing pystray
    pause
    exit /b 1
)

echo.
echo ✅ All packages installed successfully!
echo.
echo Next: Download Edge WebDriver
echo   1. Go to: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
echo   2. Download the version matching your Edge browser
echo   3. Extract msedgedriver.exe to this directory
echo.
echo Then restart your TechGuides Client Service.
echo.
pause
