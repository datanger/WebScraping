#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fixed EXE Build Script for Data Copy Tool
修复了导入问题的可执行文件构建脚本
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def clean_build_dirs():
    """清理构建目录"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"🧹 清理目录: {dir_name}")
            shutil.rmtree(dir_name)
    
    # 清理.pyc文件
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                os.remove(os.path.join(root, file))
                print(f"🧹 删除: {os.path.join(root, file)}")

def build_exe():
    """构建可执行文件"""
    print("🔨 开始构建修复版可执行文件...")
    
    # PyInstaller命令
    cmd = [
        'pyinstaller',
        '--onefile',
        '--console',
        '--name=DataCopyTool_Fixed',
        '--add-data=data_copy_modules;data_copy_modules',
        '--hidden-import=win32api',
        '--hidden-import=win32file',
        '--hidden-import=win32security',
        '--hidden-import=psutil',
        '--hidden-import=utils.confirmation_interface',
        '--hidden-import=utils.directory_tree_analyzer',
        '--hidden-import=utils.detailed_progress',
        '--hidden-import=utils.file_utils',
        '--hidden-import=utils.progress_bar',
        '--hidden-import=data_copy_modules.utils.confirmation_interface',
        '--hidden-import=data_copy_modules.utils.directory_tree_analyzer',
        '--hidden-import=data_copy_modules.utils.detailed_progress',
        '--hidden-import=data_copy_modules.utils.file_utils',
        '--hidden-import=data_copy_modules.utils.progress_bar',
        '--distpath=dist',
        '--workpath=build',
        'data_copy_modules/interactive_main.py'
    ]
    
    print(f"📝 执行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ 构建成功!")
        print("📁 可执行文件位置: dist/DataCopyTool_Fixed.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 构建失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("🔧 数据拷贝工具 - 修复版构建脚本")
    print("=" * 60)
    
    # 检查是否在正确的目录
    if not os.path.exists('data_copy_modules'):
        print("❌ 错误: 请在项目根目录运行此脚本")
        return
    
    # 清理构建目录
    clean_build_dirs()
    
    # 构建可执行文件
    if build_exe():
        print("\n" + "=" * 60)
        print("🎉 构建完成!")
        print("📁 可执行文件: dist/DataCopyTool_Fixed.exe")
        print("🔧 修复内容:")
        print("   - 修复了utils模块导入问题")
        print("   - 添加了pywin32依赖支持")
        print("   - 改进了打包兼容性")
        print("=" * 60)
    else:
        print("\n❌ 构建失败，请检查错误信息")

if __name__ == "__main__":
    main()
