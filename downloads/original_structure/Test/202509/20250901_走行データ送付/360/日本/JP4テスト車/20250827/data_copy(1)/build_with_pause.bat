@echo off
echo ========================================
echo Building Data Copy Tool with Pause Feature
echo ========================================
echo.

echo Building executable file...
pyinstaller -F --console --name=DataCopyTool_WithPause data_copy_modules/interactive_main.py

echo.
echo ========================================
echo Build completed!
echo Executable location: dist\DataCopyTool_WithPause.exe
echo Feature: Program will wait for user to press Enter before closing window
echo ========================================
pause
