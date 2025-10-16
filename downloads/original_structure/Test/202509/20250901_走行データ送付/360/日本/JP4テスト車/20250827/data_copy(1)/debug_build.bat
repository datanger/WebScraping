@echo off
echo ========================================
echo Data Copy Tool - Debug Build Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.7+ and try again
    pause
    exit /b 1
)

echo Running debug build script...
python debug_build.py

echo.
echo Debug build process completed!
pause
