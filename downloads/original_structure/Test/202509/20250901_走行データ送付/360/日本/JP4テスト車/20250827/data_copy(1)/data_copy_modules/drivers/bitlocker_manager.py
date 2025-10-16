#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BitLocker管理模块
BitLocker Management Module
"""

import os
import re
import subprocess
import logging
import getpass
import sys
from typing import Dict

logger = logging.getLogger(__name__)

def get_password_with_asterisks(prompt: str) -> str:
    """
    Get password input with asterisks displayed for each character
    Works on Windows, Linux, and macOS
    
    Args:
        prompt: The prompt message to display
        
    Returns:
        str: The entered password
    """
    import msvcrt
    import os
    
    print(prompt, end='', flush=True)
    password = ''
    
    try:
        while True:
            if os.name == 'nt':  # Windows
                char = msvcrt.getch()
                if char == b'\r':  # Enter key
                    break
                elif char == b'\b':  # Backspace
                    if len(password) > 0:
                        password = password[:-1]
                        print('\b \b', end='', flush=True)  # Erase the asterisk
                else:
                    char_str = char.decode('utf-8', errors='ignore')
                    if char_str.isprintable():
                        password += char_str
                        print('*', end='', flush=True)  # Show asterisk
            else:  # Linux/macOS
                char = sys.stdin.read(1)
                if char == '\r' or char == '\n':  # Enter key
                    break
                elif char == '\b' or ord(char) == 127:  # Backspace
                    if len(password) > 0:
                        password = password[:-1]
                        print('\b \b', end='', flush=True)  # Erase the asterisk
                else:
                    password += char
                    print('*', end='', flush=True)  # Show asterisk
    except KeyboardInterrupt:
        print("\nPassword input cancelled")
        return ""
    except Exception as e:
        print(f"\nError reading password: {e}")
        return ""
    
    print()  # New line after password input
    return password

class BitlockerManager:
    """BitLocker管理器类"""
    
    def __init__(self, os_type: str):
        """
        初始化BitLocker管理器
        
        Args:
            os_type: 操作系统类型
        """
        self.os_type = os_type
    
    def check_bitlocker_status(self, drive: str) -> str:
        """
        检查驱动器的BitLocker状态（仅Windows）
        
        Args:
            drive: 驱动器路径
            
        Returns:
            str: BitLocker状态
        """
        if self.os_type != "windows":
            return "Not Supported"
            
        try:
            # 移除冒号，因为manage-bde命令不需要
            drive_letter = drive.rstrip('\\')
            
            result = subprocess.run(
                ["manage-bde", "-status", drive_letter],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                output = result.stdout
                # 查找锁定状态
                match = re.search(r'Lock Status:\s+(.*)', output)
                if match:
                    status = match.group(1).strip()
                    if status == "Locked":
                        return "Locked"
                    elif status == "Unlocked":
                        return "Unlocked"
                    else:
                        return f"Unknown ({status})"
                else:
                    return "Not Supported"
            else:
                return "Not Supported"
                
        except subprocess.TimeoutExpired:
            logger.warning(f"检查驱动器 {drive} 的BitLocker状态超时")
            return "Timeout"
        except FileNotFoundError:
            logger.warning("manage-bde 命令不可用，可能不是Windows系统或未安装BitLocker")
            return "Not Supported"
        except Exception as e:
            logger.error(f"检查BitLocker状态时出错: {e}")
            return "Error"
    
    def unlock_all_locked_drives(self, drive_info: Dict) -> Dict[str, bool]:
        """
        使用密码解锁所有被BitLocker锁定的驱动器（仅Windows）
        
        Args:
            drive_info: 驱动器信息字典
            
        Returns:
            Dict[str, bool]: 解锁结果字典
        """
        if self.os_type != "windows":
            logger.warning("BitLocker解锁仅在Windows系统上支持")
            return {}
        
        locked_drives = [drive for drive, info in drive_info.items() 
                         if info.get('bitlocker_status') == 'Locked']
        
        if not locked_drives:
            print("No BitLocker locked drives found")
            return {}
        
        print(f"\nFound {len(locked_drives)} BitLocker locked drives:")
        for i, drive in enumerate(locked_drives, 1):
            print(f"  {i}. {drive}")
        
        # Prompt for password input
        print(f"\nUsing password to unlock all drives...")
        password = get_password_with_asterisks("Please enter BitLocker password: ")
        
        if not password:
            print("Password cannot be empty, unlock cancelled")
            return {}
        
        # Use same password to unlock all drives
        unlock_results = {}
        success_count = 0
        
        for i, drive in enumerate(locked_drives, 1):
            print(f"\n[{i}/{len(locked_drives)}] Unlocking drive {drive}...")
            success = self._unlock_with_password(drive, password)
            unlock_results[drive] = success
            if success:
                success_count += 1
                # Update status
                drive_info[drive]['bitlocker_status'] = 'Unlocked'
        
        print(f"\nUnlock completed! Successfully unlocked {success_count}/{len(locked_drives)} drives")
        return unlock_results
    
    def _unlock_with_password(self, drive: str, password: str) -> bool:
        """
        使用密码解锁BitLocker驱动器（内部方法）
        
        Args:
            drive: 驱动器路径
            password: BitLocker密码
            
        Returns:
            bool: 解锁是否成功
        """
        try:
            drive_letter = drive.rstrip('\\')
            
            ps_command = [
                "powershell",
                "-Command",
                "Unlock-BitLocker",
                "-MountPoint",
                drive_letter,
                "-Password",
                f"('{password}' | ConvertTo-SecureString -AsPlainText -Force)"
            ]
            
            logger.info(f"Using password to unlock drive {drive}...")
            process = subprocess.Popen(
                ps_command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )
            
            stdout, stderr = process.communicate(timeout=30)
            
            if process.returncode == 0:
                logger.info(f"Successfully unlocked drive {drive} with password")
                print(f"✓ Successfully unlocked drive {drive}")
                return True
            else:
                logger.error(f"Failed to unlock drive {drive} with password: {stderr}")
                print(f"✗ Failed to unlock drive {drive}: {stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout while unlocking drive {drive} with password")
            print(f"✗ Timeout while unlocking drive {drive}")
            return False
        except Exception as e:
            logger.error(f"Error while unlocking drive {drive} with password: {e}")
            print(f"✗ Error while unlocking drive {drive}: {e}")
            return False
    
    def get_unlock_methods(self) -> list:
        """
        获取可用的解锁方法
        
        Returns:
            list: 可用的解锁方法列表
        """
        if self.os_type != "windows":
            return []
        
        methods = []
        
        # 检查是否有manage-bde命令
        try:
            subprocess.run(["manage-bde", "-?"], capture_output=True, timeout=5)
            methods.append("manage-bde")
        except:
            pass
        
        # 检查是否有PowerShell
        try:
            subprocess.run(["powershell", "-Command", "Get-Command"], capture_output=True, timeout=5)
            methods.append("powershell")
        except:
            pass
        
        return methods 