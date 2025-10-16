#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单文件版PyInstaller打包脚本 - 修复编码问题
Single File PyInstaller Build Script - Fixed Encoding
"""

import os
import sys
import subprocess
import shutil

def clean_build_dirs():
    """清理构建目录"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"🧹 清理目录: {dir_name}")
            shutil.rmtree(dir_name)

def build_exe():
    """使用PyInstaller构建单文件exe"""
    print("\n🔨 开始构建单文件exe...")
    
    # 检查PyInstaller是否安装
    try:
        import PyInstaller
        print(f"✅ PyInstaller版本: {PyInstaller.__version__}")
    except ImportError:
        print("❌ PyInstaller未安装，正在安装...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)
        print("✅ PyInstaller安装完成")
    
    # 使用单文件PyInstaller命令
    cmd = [
        'pyinstaller',
        '--clean',                    # 清理临时文件
        '--noconfirm',               # 不询问覆盖
        '--onefile',                 # 单文件模式
        '--name=DataCopyTool',       # 可执行文件名称
        '--console',                 # 保留控制台窗口
        '--add-data=config.ini;.',  # 添加配置文件
        '--add-data=data_copy_modules/README.md;data_copy_modules',  # 添加说明文档
        # 必要的隐藏导入
        '--hidden-import=data_copy_modules.core.system_detector',
        '--hidden-import=data_copy_modules.drivers.drive_detector',
        '--hidden-import=data_copy_modules.drivers.bitlocker_manager',
        '--hidden-import=data_copy_modules.data_copy.qdrive_data_handler',
        '--hidden-import=data_copy_modules.data_copy.vector_data_handler',
        '--hidden-import=data_copy_modules.data_copy.copy_manager',
        '--hidden-import=data_copy_modules.utils.file_utils',
        '--hidden-import=data_copy_modules.utils.progress_bar',
        '--hidden-import=data_copy_modules.logging_utils.copy_logger',
        # 主程序入口
        'data_copy_modules/interactive_main.py'
    ]
    
    print(f"🚀 执行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ PyInstaller构建成功！")
        
        # 显示输出信息
        if result.stdout:
            print("📋 构建输出:")
            print(result.stdout)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ PyInstaller构建失败: {e}")
        if e.stderr:
            print("错误信息:")
            print(e.stderr)
        return False

def create_launcher_bat():
    """创建启动脚本 - 使用英文避免编码问题"""
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

def create_readme():
    """创建使用说明文件"""
    readme_content = '''# DataCopyTool - Single File Version

## File Description

- `DataCopyTool.exe` - Main program executable (single file, no other dependencies)
- `启动数据拷贝工具.bat` - Launch script

## Usage

### Method 1: Use Launch Script
Double-click to run `启动数据拷贝工具.bat`

### Method 2: Direct Run
Double-click to run `DataCopyTool.exe`

## Notes

1. This is a single file exe, all dependencies are packaged inside
2. The program will automatically create a `logs` directory for logs
3. First run may take a few seconds to start (extracting dependencies)
4. Ensure sufficient disk space for data copying

## Features

- ✅ Automatic drive detection
- ✅ Smart classification of source and destination drives
- ✅ BitLocker encrypted drive support
- ✅ Parallel data copying
- ✅ Progress display and logging
- ✅ Optimized directory structure

## Technical Support

If you encounter problems, please check:
1. Whether there is sufficient disk space
2. Whether drives are occupied by other programs
3. Check log files in the logs directory

## Version Features

- Portability: Single exe file, easy to distribute
- Compatibility: Contains all necessary dependencies
- Stability: Program runs stably
- Simple deployment: No installation required, run directly
'''
    
    readme_path = "dist/使用说明.txt"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✅ 创建使用说明: {readme_path}")

def main():
    """主函数"""
    print("🚀 PyInstaller单文件版打包脚本 - 修复编码问题")
    print("=" * 50)
    print("🎯 目标：创建单个exe文件，无需其他依赖")
    print("=" * 50)
    
    # 1. 清理构建目录
    print("\n1️⃣ 清理构建目录...")
    clean_build_dirs()
    
    # 2. 构建exe文件
    print("\n2️⃣ 构建exe文件...")
    if not build_exe():
        print("❌ 构建失败，程序退出")
        return
    
    # 3. 创建启动脚本
    print("\n3️⃣ 创建启动脚本...")
    create_launcher_bat()
    
    # 4. 创建使用说明
    print("\n4️⃣ 创建使用说明...")
    create_readme()
    
    # 5. 显示最终结果
    print("\n🎉 打包完成！")
    print("=" * 50)
    print("📁 生成的文件:")
    print("   dist/DataCopyTool.exe")
    print("   dist/启动数据拷贝工具.bat")
    print("   dist/使用说明.txt")
    print("\n💡 使用说明:")
    print("   1. 运行 '启动数据拷贝工具.bat' 启动程序")
    print("   2. 或直接运行 'DataCopyTool.exe'")
    print("   3. 程序会自动创建logs目录存放日志")
    
    # 6. 显示文件大小统计
    if os.path.exists("dist"):
        total_size = 0
        file_count = 0
        
        for root, dirs, files in os.walk("dist"):
            for file in files:
                file_path = os.path.join(root, file)
                total_size += os.path.getsize(file_path)
                file_count += 1
        
        total_mb = total_size / (1024 * 1024)
        print(f"\n📊 打包统计:")
        print(f"   文件总数: {file_count}")
        print(f"   总大小: {total_mb:.2f} MB")
        
        # 显示exe文件大小
        exe_path = "dist/DataCopyTool.exe"
        if os.path.exists(exe_path):
            exe_size = os.path.getsize(exe_path)
            exe_mb = exe_size / (1024 * 1024)
            print(f"   exe文件大小: {exe_mb:.2f} MB")
        
        print(f"\n🎯 版本特点:")
        print(f"   便携性：单个exe文件，方便分发")
        print(f"   兼容性：包含所有必要依赖")
        print(f"   稳定性：程序运行稳定")
        print(f"   部署简单：无需安装，直接运行")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
    except Exception as e:
        print(f"\n程序执行出错: {e}")
        import traceback
        traceback.print_exc()
