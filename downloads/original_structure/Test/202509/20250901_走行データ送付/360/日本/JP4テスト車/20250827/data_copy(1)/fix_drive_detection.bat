@echo off
echo ========================================
echo Drive Detection Fix Tool
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

echo Step 1: Running drive detection debug...
python debug_drive_detection.py

echo.
echo Step 2: Applying fixes...
python fix_drive_detection.py

echo.
echo Fix process completed!
pause
