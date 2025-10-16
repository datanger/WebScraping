#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Drive Detection Script
帮助诊断transfer和backup盘检测问题
"""

import os
import sys
import subprocess
import psutil
from pathlib import Path

def get_volume_name_windows(drive):
    """获取Windows驱动器卷名的多种方法"""
    print(f"\n🔍 检测驱动器 {drive} 的卷名:")
    
    # 方法1: win32api
    try:
        import win32api
        volume_name = win32api.GetVolumeInformation(drive)[0]
        print(f"  方法1 (win32api): '{volume_name}'")
        if volume_name:
            return volume_name
    except ImportError:
        print("  方法1 (win32api): 未安装win32api")
    except Exception as e:
        print(f"  方法1 (win32api): 错误 - {e}")
    
    # 方法2: wmic命令
    try:
        result = subprocess.run(['wmic', 'logicaldisk', 'where', f'DeviceID="{drive[:-1]}"', 'get', 'VolumeName', '/value'], 
                             capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('VolumeName='):
                    volume_name = line.split('=', 1)[1].strip()
                    print(f"  方法2 (wmic): '{volume_name}'")
                    if volume_name:
                        return volume_name
        print("  方法2 (wmic): 未找到卷名")
    except Exception as e:
        print(f"  方法2 (wmic): 错误 - {e}")
    
    # 方法3: psutil
    try:
        for partition in psutil.disk_partitions():
            if partition.device.upper() == drive.upper():
                print(f"  方法3 (psutil): '{partition.mountpoint}' - 无卷名信息")
                break
    except Exception as e:
        print(f"  方法3 (psutil): 错误 - {e}")
    
    # 方法4: 直接检查目录
    try:
        # 检查是否有echo相关的文件夹
        for item in os.listdir(drive):
            if 'echo' in item.lower():
                print(f"  方法4 (目录检查): 发现echo相关文件夹 '{item}'")
                return f"echo_{item}"
    except Exception as e:
        print(f"  方法4 (目录检查): 错误 - {e}")
    
    print("  所有方法都未找到卷名")
    return ""

def check_echo_detection(drive):
    """检查Echo盘检测逻辑"""
    volume_name = get_volume_name_windows(drive)
    
    if not volume_name:
        print(f"❌ 驱动器 {drive} 无法获取卷名")
        return False, False
    
    volume_lower = volume_name.lower()
    print(f"  卷名: '{volume_name}' -> 小写: '{volume_lower}'")
    
    # 检查backup检测
    is_backup = volume_lower.startswith('echo') and volume_lower.endswith('backup')
    print(f"  Backup检测: startswith('echo')={volume_lower.startswith('echo')}, endswith('backup')={volume_lower.endswith('backup')} -> {is_backup}")
    
    # 检查transfer检测
    is_transfer = volume_lower.startswith('echo') and not volume_lower.endswith('backup')
    print(f"  Transfer检测: startswith('echo')={volume_lower.startswith('echo')}, not endswith('backup')={not volume_lower.endswith('backup')} -> {is_transfer}")
    
    return is_backup, is_transfer

def get_available_drives():
    """获取可用驱动器列表"""
    drives = []
    if os.name == 'nt':  # Windows
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                drives.append(drive)
    else:  # Linux/Mac
        drives = [partition.mountpoint for partition in psutil.disk_partitions()]
    
    return drives

def main():
    """主函数"""
    print("🚀 Drive Detection Debug Tool")
    print("=" * 50)
    
    # 检查环境
    print(f"Python版本: {sys.version}")
    print(f"操作系统: {os.name}")
    print(f"当前工作目录: {os.getcwd()}")
    
    # 检查依赖
    print("\n📦 检查依赖:")
    try:
        import psutil
        print(f"  ✅ psutil: {psutil.__version__}")
    except ImportError:
        print("  ❌ psutil: 未安装")
    
    try:
        import win32api
        print("  ✅ win32api: 已安装")
    except ImportError:
        print("  ❌ win32api: 未安装")
    
    # 获取可用驱动器
    print("\n💾 可用驱动器:")
    drives = get_available_drives()
    for drive in drives:
        try:
            usage = psutil.disk_usage(drive)
            total_gb = usage.total / (1024**3)
            free_gb = usage.free / (1024**3)
            print(f"  {drive} - 总容量: {total_gb:.1f}GB, 可用: {free_gb:.1f}GB")
        except Exception as e:
            print(f"  {drive} - 错误: {e}")
    
    # 检查每个驱动器的Echo检测
    print("\n🔍 Echo盘检测结果:")
    echo_drives = []
    for drive in drives:
        print(f"\n{'='*30}")
        is_backup, is_transfer = check_echo_detection(drive)
        
        if is_backup:
            echo_drives.append((drive, "Backup"))
            print(f"✅ 检测为 Echo Backup 盘: {drive}")
        elif is_transfer:
            echo_drives.append((drive, "Transfer"))
            print(f"✅ 检测为 Echo Transfer 盘: {drive}")
        else:
            print(f"❌ 不是 Echo 盘: {drive}")
    
    # 总结
    print(f"\n📋 检测总结:")
    if echo_drives:
        for drive, drive_type in echo_drives:
            print(f"  {drive_type}: {drive}")
    else:
        print("  ❌ 未检测到任何 Echo 盘")
        print("\n💡 可能的原因:")
        print("  1. 卷名不是以 'echo' 开头")
        print("  2. 权限不足，无法获取卷名")
        print("  3. 驱动器未正确挂载")
        print("  4. conda环境变化导致依赖问题")
    
    # 提供解决方案
    print(f"\n🔧 解决方案:")
    print("  1. 检查驱动器卷名是否正确设置")
    print("  2. 以管理员身份运行程序")
    print("  3. 安装win32api: pip install pywin32")
    print("  4. 手动指定transfer和backup盘")
    
    input("\n按Enter键退出...")

if __name__ == "__main__":
    main()
