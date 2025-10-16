

def create_launcher_bat():
    """创建启动脚本"""
    bat_content = '''@echo off
chcp 65001 >nul
title DataCopyTool - Single File Version
echo.
echo ========================================
echo           DataCopyTool
echo           Single File Version
echo ========================================
echo.
echo Starting program...
echo.

DataCopyTool.exe

echo.
echo Program execution completed, press any key to exit...
pause >nul
'''
    
    bat_path = "dist/启动数据拷贝工具.bat"
    with open(bat_path, 'w', encoding='gbk') as f:
        f.write(bat_content)
    
    print(f"✅ 创建启动脚本: {bat_path}")
