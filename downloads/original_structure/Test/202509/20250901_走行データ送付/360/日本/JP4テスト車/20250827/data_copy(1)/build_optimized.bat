@echo off
echo ========================================
echo Building Optimized Data Copy Tool
echo ========================================
echo.

echo Building executable file...
pyinstaller -F --console --name=DataCopyTool_Optimized data_copy_modules/interactive_main.py

echo.
echo ========================================
echo Build completed!
echo Executable location: dist\DataCopyTool_Optimized.exe
echo Features:
echo   - Default high-performance mode (no mode selection)
echo   - Clean progress display (no speed/ETA)
echo   - Console window stays open after completion
echo ========================================
pause



