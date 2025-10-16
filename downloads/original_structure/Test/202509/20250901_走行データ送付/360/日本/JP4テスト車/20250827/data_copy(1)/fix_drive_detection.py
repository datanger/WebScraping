#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Drive Detection Script
修复transfer和backup盘检测问题
"""

import os
import sys
import shutil

def backup_original_file():
    """备份原始文件"""
    original_file = "data_copy_modules/drivers/drive_detector.py"
    backup_file = "data_copy_modules/drivers/drive_detector.py.backup"
    
    if os.path.exists(original_file):
        shutil.copy2(original_file, backup_file)
        print(f"✅ 已备份原始文件到: {backup_file}")
        return True
    else:
        print(f"❌ 原始文件不存在: {original_file}")
        return False

def enhance_echo_detection():
    """增强Echo盘检测逻辑"""
    print("🔧 增强Echo盘检测逻辑...")
    
    # 读取原始文件
    with open("data_copy_modules/drivers/drive_detector.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # 增强的_get_volume_name方法
    enhanced_get_volume_name = '''    def _get_volume_name(self, drive: str) -> str:
        """获取驱动器卷标 - 增强版多种方法尝试"""
        try:
            if self.os_type == "windows":
                # 方法1: 尝试使用win32api
                try:
                    import win32api
                    volume_name = win32api.GetVolumeInformation(drive)[0]
                    if volume_name:
                        logger.debug(f"Got volume name via win32api: {volume_name}")
                        return volume_name
                except ImportError:
                    logger.debug("win32api not available")
                except (PermissionError, OSError) as e:
                    logger.debug(f"win32api error: {e}")
                
                # 方法2: 尝试使用subprocess调用Windows命令
                try:
                    import subprocess
                    result = subprocess.run(['wmic', 'logicaldisk', 'where', f'DeviceID="{drive[:-1]}"', 'get', 'VolumeName', '/value'], 
                                         capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        for line in result.stdout.split('\\n'):
                            if line.startswith('VolumeName='):
                                volume_name = line.split('=', 1)[1].strip()
                                if volume_name:
                                    logger.debug(f"Got volume name via wmic: {volume_name}")
                                    return volume_name
                except Exception as e:
                    logger.debug(f"wmic error: {e}")
                
                # 方法3: 尝试使用psutil获取标签
                try:
                    for partition in psutil.disk_partitions():
                        if partition.device.upper() == drive.upper():
                            # psutil不直接提供卷名，但我们可以检查挂载点
                            logger.debug(f"Found partition via psutil: {partition.device}")
                            break
                except Exception as e:
                    logger.debug(f"psutil error: {e}")
                
                # 方法4: 检查驱动器根目录下的特殊文件/文件夹
                try:
                    # 检查是否有echo相关的文件夹或文件
                    for item in os.listdir(drive):
                        if 'echo' in item.lower():
                            logger.debug(f"Found echo-related item: {item}")
                            return f"echo_{item}"
                except Exception as e:
                    logger.debug(f"Directory listing error: {e}")
                
                # 方法5: 使用PowerShell获取卷名
                try:
                    import subprocess
                    ps_cmd = f'Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID=\'{drive[:-1]}\'" | Select-Object -ExpandProperty VolumeName'
                    result = subprocess.run(['powershell', '-Command', ps_cmd], 
                                         capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        volume_name = result.stdout.strip()
                        if volume_name and volume_name != "None":
                            logger.debug(f"Got volume name via PowerShell: {volume_name}")
                            return volume_name
                except Exception as e:
                    logger.debug(f"PowerShell error: {e}")
                
                # 方法6: 基于驱动器大小和可用空间推断
                try:
                    usage = psutil.disk_usage(drive)
                    total_gb = usage.total / (1024**3)
                    free_gb = usage.free / (1024**3)
                    
                    # 如果驱动器很大且有很多可用空间，可能是transfer盘
                    if total_gb > 100 and free_gb > 50:
                        logger.debug(f"Large drive detected: {total_gb:.1f}GB total, {free_gb:.1f}GB free")
                        # 不直接返回，继续尝试其他方法
                except Exception as e:
                    logger.debug(f"Disk usage check error: {e}")
                
                logger.debug(f"Could not get volume name for {drive}")
                return ""
            else:
                # Linux/Mac implementation
                try:
                    for partition in psutil.disk_partitions():
                        if partition.mountpoint == drive:
                            return partition.device
                except Exception as e:
                    logger.debug(f"Linux/Mac volume name error: {e}")
                    return ""
        except Exception as e:
            logger.debug(f"Error getting volume name for {drive}: {e}")
            return ""'''
    
    # 增强的Echo检测方法
    enhanced_echo_backup = '''    def _is_echo_backup_drive(self, drive: str) -> bool:
        """
        Check if drive is Echo backup drive (Echo*backup) - Enhanced version
        
        Args:
            drive: Drive path
            
        Returns:
            bool: True if is Echo backup drive
        """
        try:
            # 方法1: 检查卷名
            volume_name = self._get_volume_name(drive).lower()
            if volume_name:
                is_echo_backup = volume_name.startswith('echo') and volume_name.endswith('backup')
                if is_echo_backup:
                    logger.info(f"Drive {drive} identified as Echo backup via volume name: {volume_name}")
                    return True
            
            # 方法2: 检查驱动器根目录下的特殊文件/文件夹
            try:
                for item in os.listdir(drive):
                    item_lower = item.lower()
                    if 'echo' in item_lower and 'backup' in item_lower:
                        logger.info(f"Drive {drive} identified as Echo backup via directory: {item}")
                        return True
            except Exception as e:
                logger.debug(f"Error checking directory for backup drive {drive}: {e}")
            
            # 方法3: 检查驱动器大小特征（backup盘通常很大）
            try:
                usage = psutil.disk_usage(drive)
                total_gb = usage.total / (1024**3)
                if total_gb > 500:  # 大于500GB可能是backup盘
                    logger.debug(f"Drive {drive} is large ({total_gb:.1f}GB), might be backup drive")
                    # 不直接返回True，需要更多证据
            except Exception as e:
                logger.debug(f"Error checking disk usage for backup drive {drive}: {e}")
            
            return False
        except Exception as e:
            logger.debug(f"Error checking Echo backup drive {drive}: {e}")
            return False'''
    
    enhanced_echo_transfer = '''    def _is_echo_transfer_drive(self, drive: str) -> bool:
        """
        Check if drive is Echo transfer drive (Echo* but not ending with backup) - Enhanced version
        
        Args:
            drive: Drive path
            
        Returns:
            bool: True if is Echo transfer drive
        """
        try:
            # 方法1: 检查卷名
            volume_name = self._get_volume_name(drive).lower()
            if volume_name:
                is_echo_transfer = volume_name.startswith('echo') and not volume_name.endswith('backup')
                if is_echo_transfer:
                    logger.info(f"Drive {drive} identified as Echo transfer via volume name: {volume_name}")
                    return True
            
            # 方法2: 检查驱动器根目录下的特殊文件/文件夹
            try:
                for item in os.listdir(drive):
                    item_lower = item.lower()
                    if 'echo' in item_lower and 'backup' not in item_lower:
                        logger.info(f"Drive {drive} identified as Echo transfer via directory: {item}")
                        return True
            except Exception as e:
                logger.debug(f"Error checking directory for transfer drive {drive}: {e}")
            
            # 方法3: 检查驱动器大小特征（transfer盘通常中等大小）
            try:
                usage = psutil.disk_usage(drive)
                total_gb = usage.total / (1024**3)
                if 100 < total_gb < 500:  # 100GB-500GB可能是transfer盘
                    logger.debug(f"Drive {drive} is medium size ({total_gb:.1f}GB), might be transfer drive")
                    # 不直接返回True，需要更多证据
            except Exception as e:
                logger.debug(f"Error checking disk usage for transfer drive {drive}: {e}")
            
            return False
        except Exception as e:
            logger.debug(f"Error checking Echo transfer drive {drive}: {e}")
            return False'''
    
    # 替换原始方法
    replacements = [
        (r'def _get_volume_name\(self, drive: str\) -> str:.*?return ""', enhanced_get_volume_name, re.DOTALL),
        (r'def _is_echo_backup_drive\(self, drive: str\) -> bool:.*?return False', enhanced_echo_backup, re.DOTALL),
        (r'def _is_echo_transfer_drive\(self, drive: str\) -> bool:.*?return False', enhanced_echo_transfer, re.DOTALL)
    ]
    
    import re
    for pattern, replacement, flags in replacements:
        content = re.sub(pattern, replacement, content, flags=flags)
    
    # 写回文件
    with open("data_copy_modules/drivers/drive_detector.py", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ 已增强Echo盘检测逻辑")

def add_fallback_detection():
    """添加备用检测方法"""
    print("🔧 添加备用检测方法...")
    
    # 读取文件
    with open("data_copy_modules/drivers/drive_detector.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # 在_perform_automatic_identification方法中添加备用检测
    fallback_code = '''
        # Fallback detection for transfer and backup drives if not found
        if not transfer_drives and not backup_drives:
            logger.info("No Echo drives detected, trying fallback detection...")
            
            # Get all available drives that haven't been classified
            classified_drives = set(qdrive_drives + vector_drives)
            unclassified_drives = [drive for drive in available_drives if drive not in classified_drives]
            
            if len(unclassified_drives) >= 2:
                # Sort by size, larger drive is backup, smaller is transfer
                drive_sizes = []
                for drive in unclassified_drives:
                    try:
                        usage = psutil.disk_usage(drive)
                        total_gb = usage.total / (1024**3)
                        drive_sizes.append((drive, total_gb))
                    except Exception as e:
                        logger.debug(f"Error getting size for {drive}: {e}")
                        drive_sizes.append((drive, 0))
                
                # Sort by size (descending)
                drive_sizes.sort(key=lambda x: x[1], reverse=True)
                
                if len(drive_sizes) >= 2:
                    # Largest drive as backup, second largest as transfer
                    backup_drives.append(drive_sizes[0][0])
                    transfer_drives.append(drive_sizes[1][0])
                    logger.info(f"Fallback detection: Backup={drive_sizes[0][0]} ({drive_sizes[0][1]:.1f}GB), Transfer={drive_sizes[1][0]} ({drive_sizes[1][1]:.1f}GB)")
                elif len(drive_sizes) == 1:
                    # Only one unclassified drive, make it transfer
                    transfer_drives.append(drive_sizes[0][0])
                    logger.info(f"Fallback detection: Transfer={drive_sizes[0][0]} ({drive_sizes[0][1]:.1f}GB)")
        elif not transfer_drives and backup_drives:
            # Only backup found, try to find transfer
            logger.info("Only backup drive found, looking for transfer drive...")
            classified_drives = set(qdrive_drives + vector_drives + backup_drives)
            unclassified_drives = [drive for drive in available_drives if drive not in classified_drives]
            
            if unclassified_drives:
                # Use the largest unclassified drive as transfer
                drive_sizes = []
                for drive in unclassified_drives:
                    try:
                        usage = psutil.disk_usage(drive)
                        total_gb = usage.total / (1024**3)
                        drive_sizes.append((drive, total_gb))
                    except Exception as e:
                        logger.debug(f"Error getting size for {drive}: {e}")
                        drive_sizes.append((drive, 0))
                
                if drive_sizes:
                    drive_sizes.sort(key=lambda x: x[1], reverse=True)
                    transfer_drives.append(drive_sizes[0][0])
                    logger.info(f"Fallback detection: Transfer={drive_sizes[0][0]} ({drive_sizes[0][1]:.1f}GB)")
        elif not backup_drives and transfer_drives:
            # Only transfer found, try to find backup
            logger.info("Only transfer drive found, looking for backup drive...")
            classified_drives = set(qdrive_drives + vector_drives + transfer_drives)
            unclassified_drives = [drive for drive in available_drives if drive not in classified_drives]
            
            if unclassified_drives:
                # Use the largest unclassified drive as backup
                drive_sizes = []
                for drive in unclassified_drives:
                    try:
                        usage = psutil.disk_usage(drive)
                        total_gb = usage.total / (1024**3)
                        drive_sizes.append((drive, total_gb))
                    except Exception as e:
                        logger.debug(f"Error getting size for {drive}: {e}")
                        drive_sizes.append((drive, 0))
                
                if drive_sizes:
                    drive_sizes.sort(key=lambda x: x[1], reverse=True)
                    backup_drives.append(drive_sizes[0][0])
                    logger.info(f"Fallback detection: Backup={drive_sizes[0][0]} ({drive_sizes[0][1]:.1f}GB)")
'''
    
    # 在return语句之前插入备用检测代码
    import re
    pattern = r'(\s+return qdrive_drives, vector_drives, transfer_drives, backup_drives)'
    replacement = fallback_code + r'\1'
    content = re.sub(pattern, replacement, content)
    
    # 写回文件
    with open("data_copy_modules/drivers/drive_detector.py", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ 已添加备用检测方法")

def main():
    """主函数"""
    print("🚀 Drive Detection Fix Tool")
    print("=" * 50)
    
    # 检查文件是否存在
    if not os.path.exists("data_copy_modules/drivers/drive_detector.py"):
        print("❌ 找不到drive_detector.py文件")
        return False
    
    # 备份原始文件
    if not backup_original_file():
        return False
    
    try:
        # 增强Echo检测逻辑
        enhance_echo_detection()
        
        # 添加备用检测方法
        add_fallback_detection()
        
        print("\n🎉 修复完成!")
        print("\n📋 修复内容:")
        print("  1. 增强了卷名获取方法（6种方法）")
        print("  2. 增强了Echo盘检测逻辑（3种方法）")
        print("  3. 添加了备用检测方法（基于驱动器大小）")
        print("  4. 增加了详细的调试日志")
        
        print("\n💡 使用建议:")
        print("  1. 运行 debug_drive_detection.py 检查当前状态")
        print("  2. 重新运行主程序测试检测效果")
        print("  3. 如果仍有问题，可以手动指定transfer和backup盘")
        
        return True
        
    except Exception as e:
        print(f"❌ 修复过程中出错: {e}")
        print("请检查文件权限和Python环境")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n💡 故障排除:")
        print("  1. 确保以管理员身份运行")
        print("  2. 检查文件权限")
        print("  3. 确保Python环境正确")
    
    input("\n按Enter键退出...")
