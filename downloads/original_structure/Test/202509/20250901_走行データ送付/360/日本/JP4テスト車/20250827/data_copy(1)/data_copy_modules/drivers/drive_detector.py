#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Drive Detection Module
"""

import os
import platform
import psutil
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

class DriveDetector:
    """Drive Detector Class"""
    
    def __init__(self):
        """Initialize drive detector"""
        self.drives = []
        self.system_drives = []
        self.source_drives = []
        self.destination_drives = []
        self.drive_info = {}
        self.os_type = self._detect_os()
        
        # Data copy related attributes
        self.qdrive_drives = []  # Qdrive data drives (201, 203, 230, 231)
        self.vector_drives = []  # Vector data drives (USB interface)
        self.transfer_drives = []  # transfer ssd target drives
        self.backup_drives = []   # backup ssd target drives
        
        logger.info(f"Detected operating system: {self.os_type}")
    
    def _detect_os(self) -> str:
        """Detect operating system type"""
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        elif system == "linux":
            return "linux"
        elif system == "darwin":
            return "macos"
        else:
            return "unknown"
    
    def detect_all_drives(self) -> List[str]:
        """
        Detect all available drives in the system - including encrypted drives
        
        Returns:
            List[str]: Drive path list
        """
        try:
            drives = []
            
            if self.os_type == "windows":
                # Windows system: detect all drive letters, including encrypted ones
                for partition in psutil.disk_partitions():
                    if partition.device:
                        # Check if drive exists (including encrypted ones)
                        if os.path.exists(partition.device):
                            drives.append(partition.device)
                            logger.debug(f"Detected drive: {partition.device}")
                        else:
                            # Even if path doesn't exist, try to add (might be encrypted drive)
                            logger.debug(f"Detected possibly encrypted drive: {partition.device} (path doesn't exist)")
                            drives.append(partition.device)
            else:
                # Linux/macOS system: detect mount points
                for partition in psutil.disk_partitions():
                    if partition.mountpoint and self._is_drive_accessible(partition.mountpoint):
                        drives.append(partition.mountpoint)
            
            self.drives = drives
            logger.info(f"Detected {len(drives)} drives: {drives}")
            return drives
            
        except Exception as e:
            logger.error(f"Error detecting drives: {e}")
            return []
    
    def _is_drive_accessible(self, drive_path: str) -> bool:
        """
        Check if drive is accessible - including encrypted drives
        
        Args:
            drive_path: Drive path
            
        Returns:
            bool: Whether accessible
        """
        try:
            # Check if path exists (including encrypted drives)
            if not os.path.exists(drive_path):
                return False
            
            # Try to get basic information, don't scan content
            if self.os_type == "windows":
                # Windows: check if drive letter is accessible, including encrypted ones
                try:
                    # Try to access drive root directory
                    os.listdir(drive_path)
                    return True
                except (PermissionError, OSError) as e:
                    # Permission error might be encrypted drive, still consider accessible
                    logger.debug(f"Drive {drive_path} access restricted, might be encrypted drive: {e}")
                    return True
                except Exception as e:
                    logger.debug(f"Drive {drive_path} access check failed: {e}")
                    return False
            else:
                # Linux/macOS: check if mount point is accessible
                return os.access(drive_path, os.R_OK)
                
        except (PermissionError, OSError) as e:
            # Permission error might be encrypted drive, still consider accessible
            logger.debug(f"Drive {drive_path} access restricted, might be encrypted drive: {e}")
            return True
        except Exception as e:
            logger.debug(f"Drive {drive_path} access check failed: {e}")
            return False
    
    def get_system_drives(self) -> List[str]:
        """
        Get system drive list
        
        Returns:
            List[str]: System drive list
        """
        system_drives = []
        
        try:
            if self.os_type == "windows":
                # Windows system: detect system drive
                system_root = os.environ.get('SystemRoot', 'C:\\Windows')
                system_drive = os.path.splitdrive(system_root)[0] + '\\'
                if system_drive in self.drives:
                    system_drives.append(system_drive)
                
                # Detect other system-related drives
                for drive in self.drives:
                    if self._is_windows_system_drive(drive):
                        if drive not in system_drives:
                            system_drives.append(drive)
                            
            elif self.os_type == "linux":
                # Linux system: detect system mount points
                root_drive = '/'
                if root_drive in self.drives:
                    system_drives.append(root_drive)
                
                # Check other system mount points
                system_mounts = ['/boot', '/boot/efi', '/usr', '/var', '/tmp', '/proc', '/sys']
                for mount in system_mounts:
                    if mount in self.drives:
                        system_drives.append(mount)
                        
            elif self.os_type == "macos":
                # macOS system: detect system mount points
                root_drive = '/'
                if root_drive in self.drives:
                    system_drives.append(root_drive)
                
                # Check other system mount points
                system_mounts = ['/System', '/Applications', '/Users', '/private', '/Volumes']
                for mount in system_mounts:
                    if mount in self.drives:
                        system_drives.append(mount)
                        
        except Exception as e:
            logger.error(f"Error getting system drives: {e}")
            if self.os_type == "windows":
                system_drives = ['C:\\']
            else:
                system_drives = ['/']
        
        self.system_drives = system_drives
        logger.info(f"Identified system drives: {system_drives}")
        return system_drives
    
    def _is_windows_system_drive(self, drive: str) -> bool:
        """Determine if Windows drive is system-related - optimized version, no content scanning"""
        try:
            # Determine actual system drive from SystemRoot (e.g., C:\Windows)
            system_root = os.environ.get('SystemRoot', 'C\\Windows')
            system_drive = os.path.splitdrive(system_root)[0] + '\\'
            if drive == system_drive:
                return True
            
            # Check if it's an EFI partition (judge by volume label, no content scanning)
            if self._is_efi_partition(drive):
                return True
            
            # Check if it's a recovery partition (judge by volume label, no content scanning)
            if self._is_recovery_partition(drive):
                return True
                
        except Exception:
            pass
            
        return False
    
    def _is_efi_partition(self, drive: str) -> bool:
        """Check if it's an EFI partition"""
        try:
            efi_path = os.path.join(drive, 'EFI')
            return os.path.exists(efi_path) and os.path.isdir(efi_path)
        except:
            return False
    
    def _is_recovery_partition(self, drive: str) -> bool:
        """Check if it's a recovery partition"""
        try:
            recovery_path = os.path.join(drive, 'Recovery')
            return os.path.exists(recovery_path) and os.path.isdir(recovery_path)
        except:
            return False
    
    def exclude_system_drives(self) -> List[str]:
        """
        Exclude system drives, return drives available for backup
        
        Returns:
            List[str]: Drive list after excluding system drives
        """
        if not self.system_drives:
            self.get_system_drives()
            
        available_drives = [drive for drive in self.drives 
                           if drive not in self.system_drives]
        
        logger.info(f"Available drives after excluding system drives: {available_drives}")
        return available_drives
    
    def classify_drives(self) -> Tuple[List[str], List[str]]:
        """
        Classify drives as source data drives and target backup drives
        
        Returns:
            Tuple[List[str], List[str]]: (Source data drive list, Target backup drive list)
        """
        available_drives = self.exclude_system_drives()
        
        source_drives = []
        destination_drives = []
        
        for drive in available_drives:
            if self._is_source_drive(drive):
                source_drives.append(drive)
            elif self._is_destination_drive(drive):
                destination_drives.append(drive)
            else:
                # If cannot determine, default as target drive
                destination_drives.append(drive)
        
        self.source_drives = source_drives
        self.destination_drives = destination_drives
        
        logger.info(f"Drive classification completed:")
        logger.info(f"  Source data drives: {source_drives}")
        logger.info(f"  Target backup drives: {destination_drives}")
        
        return source_drives, destination_drives
    
    def _is_source_drive(self, drive: str) -> bool:
        """
        Determine if drive is a source data drive - optimized version, no content scanning
        
        Args:
            drive: Drive path
            
        Returns:
            bool: Whether it's a source data drive
        """
        try:
            # Only check root directory, no deep scanning
            if not os.access(drive, os.R_OK):
                return False
            
            # Quick check of folders in root directory
            try:
                entries = os.listdir(drive)
                # Check if contains data-related folders
                data_folders = ['data', 'record', 'logs', 'backup', 'archive', 'source', 'raw']
                for folder in data_folders:
                    if folder in entries:
                        return True
                
                # Check if volume name contains data-related keywords
                volume_name = self._get_volume_name(drive).lower()
                data_keywords = ['data', 'record', 'log', 'source', 'raw', '201', '203', '230', '231']
                if any(keyword in volume_name for keyword in data_keywords):
                    return True
                    
            except (PermissionError, OSError):
                # Permission error, might be encrypted drive, default as source drive
                logger.debug(f"Drive {drive} access restricted, might be encrypted drive, marked as source drive")
                return True
                
        except Exception:
            pass
            
        return False
    
    def _is_destination_drive(self, drive: str) -> bool:
        """
        Determine if drive is a target backup drive - optimized version, no content scanning
        
        Args:
            drive: Drive path
            
        Returns:
            bool: Whether it's a target backup drive
        """
        try:
            # Check if volume name contains backup-related keywords
            volume_name = self._get_volume_name(drive).lower()
            backup_keywords = ['backup', 'archive', 'copy', 'mirror', 'destination', 'target', 'temp', 'transfer']
            if any(keyword in volume_name for keyword in backup_keywords):
                return True
            
            # Check if drive is almost empty (quick check)
            if self._is_disk_almost_empty(drive):
                return True
                    
        except Exception:
            pass
            
        return False
    
    def _is_disk_almost_empty(self, drive: str) -> bool:
        """
        Determine if drive is almost empty - optimized version, no deep scanning
        
        Args:
            drive: Drive path
            
        Returns:
            bool: Whether almost empty
        """
        try:
            if not os.access(drive, os.R_OK):
                return False
            
            # Define folders to exclude based on operating system
            if self.os_type == "windows":
                excluded_folders = ['$RECYCLE.BIN', 'System Volume Information', 'found.000']
            elif self.os_type == "linux":
                excluded_folders = ['.Trash-1000', '.cache', 'lost+found']
            elif self.os_type == "macos":
                excluded_folders = ['.Trashes', '.Spotlight-V100', '.fseventsd']
            else:
                excluded_folders = []
            
            try:
                entries = os.listdir(drive)
                # Filter out excluded folders
                filtered_entries = [entry for entry in entries 
                                  if entry not in excluded_folders 
                                  and not entry.startswith('.')]
                
                # If filtered entries count is small, consider disk almost empty
                return len(filtered_entries) <= 2
                
            except (PermissionError, OSError):
                # Permission error, might be encrypted drive, default as target drive
                return True
                
        except Exception:
            return False
    
    def get_drive_information(self) -> Dict[str, Dict]:
        """
        Get basic information of all drives - including encrypted drives
        
        Returns:
            Dict[str, Dict]: Drive information dictionary
        """
        drive_info = {}
        
        for drive in self.drives:
            try:
                # Check if drive is accessible
                is_accessible = False
                try:
                    os.listdir(drive)
                    is_accessible = True
                except (PermissionError, OSError):
                    is_accessible = False
                
                # Get disk usage (if accessible)
                total = used = free = 0
                if is_accessible:
                    try:
                        usage = psutil.disk_usage(drive)
                        total = usage.total
                        used = usage.used
                        free = usage.free
                    except (PermissionError, OSError):
                        pass
                
                # Get file system information
                fs_type = "Unknown"
                try:
                    for partition in psutil.disk_partitions():
                        if (self.os_type == "windows" and partition.device == drive) or \
                           (self.os_type != "windows" and partition.mountpoint == drive):
                            fs_type = partition.fstype or "Unknown"
                            break
                except:
                    fs_type = "Unknown"
                
                # Get volume label information (quick get)
                volume_name = self._get_volume_name(drive)
                
                # Determine if it's an encrypted drive
                is_encrypted = False
                if not is_accessible:
                    is_encrypted = True
                elif fs_type == "Unknown" and not is_accessible:
                    is_encrypted = True
                
                # Further check if it's a BitLocker encrypted drive
                if is_encrypted and self.os_type == "windows":
                    try:
                        # Try using manage-bde command to check BitLocker status
                        import subprocess
                        drive_letter = drive.rstrip('\\')
                        result = subprocess.run(
                            ["manage-bde", "-status", drive_letter],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if result.returncode == 0:
                            output = result.stdout
                            if "Lock Status:" in output:
                                is_encrypted = True
                                logger.debug(f"Drive {drive} identified as BitLocker encrypted drive")
                    except Exception as e:
                        logger.debug(f"Error checking BitLocker status for drive {drive}: {e}")
                        # Even if check fails, still mark as encrypted drive
                        is_encrypted = True
                
                # Get BitLocker status (if available)
                bitlocker_status = "Unknown"
                if is_encrypted and self.os_type == "windows":
                    try:
                        import subprocess
                        drive_letter = drive.rstrip('\\')
                        result = subprocess.run(
                            ["manage-bde", "-status", drive_letter],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if result.returncode == 0:
                            output = result.stdout
                            # Find lock status (support Chinese and English)
                            import re
                            
                            # Try to match Chinese status first (because system is Chinese)
                            match = re.search(r'锁定状态:\s+(.*)', output)
                            if match:
                                status_text = match.group(1).strip()
                                if "已锁定" in status_text:
                                    bitlocker_status = "Locked"
                                elif "已解锁" in status_text:
                                    bitlocker_status = "Unlocked"
                                else:
                                    bitlocker_status = "Unknown"
                            else:
                                # Try to match English status
                                match = re.search(r'Lock Status:\s+(.*)', output)
                                if match:
                                    status_text = match.group(1).strip()
                                    if "Locked" in status_text:
                                        bitlocker_status = "Locked"
                                    elif "Unlocked" in status_text:
                                        bitlocker_status = "Unlocked"
                                    else:
                                        bitlocker_status = "Unknown"
                                else:
                                    # If no clear status found, check other indicators
                                    if "BitLocker" in output:
                                        # Check if contains lock-related keywords
                                        if any(keyword in output for keyword in ["已锁定", "Locked", "锁定"]):
                                            bitlocker_status = "Locked"
                                        elif any(keyword in output for keyword in ["已解锁", "Unlocked", "解锁"]):
                                            bitlocker_status = "Unlocked"
                                        else:
                                            # 有BitLocker但状态不明，默认认为已锁定
                                            bitlocker_status = "Locked"
                                    else:
                                        # 如果驱动器被识别为加密但manage-bde命令没有返回BitLocker信息
                                        # 可能是因为驱动器被锁定，默认认为已锁定
                                        bitlocker_status = "Locked"
                        else:
                            # 命令失败，但驱动器被识别为加密，默认认为已锁定
                            bitlocker_status = "Locked"
                    except Exception as e:
                        logger.debug(f"获取驱动器 {drive} 的BitLocker状态时出错: {e}")
                        # 出错时，如果驱动器被识别为加密，默认认为已锁定
                        bitlocker_status = "Locked"
                
                drive_info[drive] = {
                    'total': total,
                    'used': used,
                    'free': free,
                    'volume_name': volume_name,
                    'fs_type': fs_type,
                    'is_accessible': is_accessible,
                    'is_encrypted': is_encrypted,
                    'bitlocker_status': bitlocker_status,
                    'is_system': drive in self.system_drives,
                    'is_source': drive in self.source_drives,
                    'is_destination': drive in self.destination_drives
                }
                
            except Exception as e:
                logger.error(f"获取驱动器 {drive} 信息时出错: {e}")
                drive_info[drive] = {'error': str(e)}
        
        self.drive_info = drive_info
        return drive_info
    
    def _get_volume_name(self, drive: str) -> str:
        """获取驱动器卷标 - 多种方法尝试"""
        try:
            if self.os_type == "windows":
                # 方法1: 尝试使用win32api
                try:
                    import win32api
                    volume_name = win32api.GetVolumeInformation(drive)[0]
                    if volume_name:
                        return volume_name
                except ImportError:
                    pass
                except (PermissionError, OSError):
                    pass
                
                # 方法2: 尝试使用subprocess调用Windows命令
                try:
                    import subprocess
                    result = subprocess.run(['wmic', 'logicaldisk', 'where', f'DeviceID="{drive[:-1]}"', 'get', 'VolumeName', '/value'], 
                                         capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if line.startswith('VolumeName='):
                                volume_name = line.split('=', 1)[1].strip()
                                if volume_name:
                                    return volume_name
                except Exception:
                    pass
                
                # 方法3: 尝试使用psutil获取标签
                try:
                    for partition in psutil.disk_partitions():
                        if partition.device == drive and hasattr(partition, 'label') and partition.label:
                            return partition.label
                except Exception:
                    pass
                
                # 方法4: 尝试读取驱动器属性文件
                try:
                    label_file = os.path.join(drive, 'System Volume Information', 'WPSettings.dat')
                    if os.path.exists(label_file):
                        # 这是一个简化的方法，实际可能需要更复杂的解析
                        return "System"
                except Exception:
                    pass
                
                # 方法5: 使用盘符作为备选
                return f"Drive_{drive[:-1]}"
            else:
                # Linux/macOS系统：使用路径名
                return os.path.basename(drive) or drive
        except Exception:
            return f"Drive_{drive[:-1]}" if drive.endswith('\\') else drive
    
    def _has_camera_fc_mp4_files(self, drive: str) -> bool:
        """
        Check if drive contains camera_fc*.mp4 files (indicates 201 drive)
        
        Args:
            drive: Drive path
            
        Returns:
            bool: True if contains camera_fc*.mp4 files
        """
        try:
            if not os.access(drive, os.R_OK):
                return False
            
            # Search for camera_fc*.mp4 files in the drive
            for root, dirs, files in os.walk(drive):
                for file in files:
                    if file.startswith('camera_fc') and file.endswith('.mp4'):
                        logger.debug(f"Found camera_fc*.mp4 file: {os.path.join(root, file)}")
                        return True
                # Limit search depth to avoid long scans
                if len(root.split(os.sep)) - len(drive.split(os.sep)) > 3:
                    dirs.clear()
            
            return False
        except Exception as e:
            logger.debug(f"Error checking camera_fc*.mp4 files in {drive}: {e}")
            return False
    
    def _has_camera_rc_mp4_files(self, drive: str) -> bool:
        """
        Check if drive contains camera_rc*.mp4 files (indicates 203 drive)
        
        Args:
            drive: Drive path
            
        Returns:
            bool: True if contains camera_rc*.mp4 files
        """
        try:
            if not os.access(drive, os.R_OK):
                return False
            
            # Search for camera_rc*.mp4 files in the drive
            for root, dirs, files in os.walk(drive):
                for file in files:
                    if file.startswith('camera_rc') and file.endswith('.mp4'):
                        logger.debug(f"Found camera_rc*.mp4 file: {os.path.join(root, file)}")
                        return True
                # Limit search depth to avoid long scans
                if len(root.split(os.sep)) - len(drive.split(os.sep)) > 3:
                    dirs.clear()
            
            return False
        except Exception as e:
            logger.debug(f"Error checking camera_rc*.mp4 files in {drive}: {e}")
            return False
    
    def _has_data_lidar_top_folder(self, drive: str) -> bool:
        """
        Check if drive contains data_lidar_top folder (indicates 230 drive)
        
        Args:
            drive: Drive path
            
        Returns:
            bool: True if contains data_lidar_top folder
        """
        try:
            if not os.access(drive, os.R_OK):
                return False
            
            # Search for data_lidar_top folder
            for root, dirs, files in os.walk(drive):
                if 'data_lidar_top' in dirs:
                    logger.debug(f"Found data_lidar_top folder: {os.path.join(root, 'data_lidar_top')}")
                    return True
                # Limit search depth to avoid long scans
                if len(root.split(os.sep)) - len(drive.split(os.sep)) > 3:
                    dirs.clear()
            
            return False
        except Exception as e:
            logger.debug(f"Error checking data_lidar_top folder in {drive}: {e}")
            return False
    
    def _has_data_lidar_front_folder(self, drive: str) -> bool:
        """
        Check if drive contains data_lidar_front folder (indicates 231 drive)
        
        Args:
            drive: Drive path
            
        Returns:
            bool: True if contains data_lidar_front folder
        """
        try:
            if not os.access(drive, os.R_OK):
                return False
            
            # Search for data_lidar_front folder
            for root, dirs, files in os.walk(drive):
                if 'data_lidar_front' in dirs:
                    logger.debug(f"Found data_lidar_front folder: {os.path.join(root, 'data_lidar_front')}")
                    return True
                # Limit search depth to avoid long scans
                if len(root.split(os.sep)) - len(drive.split(os.sep)) > 3:
                    dirs.clear()
            
            return False
        except Exception as e:
            logger.debug(f"Error checking data_lidar_front folder in {drive}: {e}")
            return False
    
    def _has_logs_folder(self, drive: str) -> bool:
        """
        Check if drive contains Logs or logs folder (indicates Vector drive)
        
        Args:
            drive: Drive path
            
        Returns:
            bool: True if contains Logs or logs folder
        """
        try:
            if not os.access(drive, os.R_OK):
                return False
            
            # Check for Logs or logs folder in root directory
            entries = os.listdir(drive)
            if 'Logs' in entries or 'logs' in entries:
                logger.debug(f"Found Logs/logs folder in {drive}")
                return True
            
            return False
        except Exception as e:
            logger.debug(f"Error checking Logs/logs folder in {drive}: {e}")
            return False
    
    def _is_echo_backup_drive(self, drive: str) -> bool:
        """
        Check if drive is Echo backup drive (Echo*backup)
        
        Args:
            drive: Drive path
            
        Returns:
            bool: True if is Echo backup drive
        """
        try:
            volume_name = self._get_volume_name(drive).lower()
            return volume_name.startswith('echo') and volume_name.endswith('backup')
        except Exception as e:
            logger.debug(f"Error checking Echo backup drive {drive}: {e}")
            return False
    
    def _is_echo_transfer_drive(self, drive: str) -> bool:
        """
        Check if drive is Echo transfer drive (Echo* but not ending with backup)
        
        Args:
            drive: Drive path
            
        Returns:
            bool: True if is Echo transfer drive
        """
        try:
            volume_name = self._get_volume_name(drive).lower()
            return volume_name.startswith('echo') and not volume_name.endswith('backup')
        except Exception as e:
            logger.debug(f"Error checking Echo transfer drive {drive}: {e}")
            return False

    def identify_data_drives(self, require_confirmation: bool = True) -> Tuple[List[str], List[str], List[str], List[str]]:
        """
        Automatically identify Qdrive (201, 203, 230, 231), Vector, transfer and backup drives
        
        Args:
            require_confirmation: Whether to require user confirmation
            
        Returns:
            Tuple[List[str], List[str], List[str], List[str]]: (qdrive_drives, vector_drives, transfer_drives, backup_drives)
        """
        # Perform automatic identification
        qdrive_drives, vector_drives, transfer_drives, backup_drives = self._perform_automatic_identification()
        
        # If confirmation is required, show results and get user confirmation
        if require_confirmation:
            return self._get_user_confirmation(qdrive_drives, vector_drives, transfer_drives, backup_drives)
        else:
            return qdrive_drives, vector_drives, transfer_drives, backup_drives
    
    def _perform_automatic_identification(self) -> Tuple[List[str], List[str], List[str], List[str]]:
        """Perform automatic drive identification"""
        # First detect all drives
        self.detect_all_drives()
        available_drives = self.exclude_system_drives()
        
        qdrive_201_drives = []
        qdrive_203_drives = []
        qdrive_230_drives = []
        qdrive_231_drives = []
        vector_drives = []
        transfer_drives = []
        backup_drives = []
        
        for drive in available_drives:
            try:
                logger.info(f"Analyzing drive: {drive}")
                
                # First check volume name for Echo drives (highest priority)
                volume_name = self._get_volume_name(drive)
                logger.debug(f"Drive {drive} volume name: '{volume_name}'")
                
                # 1. Check for Echo backup drive (Echo*backup) - highest priority
                if self._is_echo_backup_drive(drive):
                    backup_drives.append(drive)
                    logger.info(f"Identified Echo backup drive: {drive} (volume: {volume_name})")
                    continue
                
                # 2. Check for Echo transfer drive (Echo* but not ending with backup) - high priority
                if self._is_echo_transfer_drive(drive):
                    transfer_drives.append(drive)
                    logger.info(f"Identified Echo transfer drive: {drive} (volume: {volume_name})")
                    continue
                
                # 3. Check for camera_fc*.mp4 files (201 drive)
                has_fc = self._has_camera_fc_mp4_files(drive)
                if has_fc:
                    qdrive_201_drives.append(drive)
                    logger.info(f"Identified Qdrive 201: {drive} (contains camera_fc*.mp4 files)")
                    continue
                
                # 4. Check for camera_rc*.mp4 files (203 drive)
                has_rc = self._has_camera_rc_mp4_files(drive)
                if has_rc:
                    qdrive_203_drives.append(drive)
                    logger.info(f"Identified Qdrive 203: {drive} (contains camera_rc*.mp4 files)")
                    continue
                
                # 5. Check for data_lidar_top folder (230 drive)
                has_lidar_top = self._has_data_lidar_top_folder(drive)
                if has_lidar_top:
                    qdrive_230_drives.append(drive)
                    logger.info(f"Identified Qdrive 230: {drive} (contains data_lidar_top folder)")
                    continue
                
                # 6. Check for data_lidar_front folder (231 drive)
                has_lidar_front = self._has_data_lidar_front_folder(drive)
                if has_lidar_front:
                    qdrive_231_drives.append(drive)
                    logger.info(f"Identified Qdrive 231: {drive} (contains data_lidar_front folder)")
                    continue
                
                # 7. Check for Logs or logs folder (Vector drive)
                if self._has_logs_folder(drive):
                    vector_drives.append(drive)
                    logger.info(f"Identified Vector drive: {drive} (contains Logs/logs folder)")
                    continue
                
                # If cannot be identified, skip it (don't default to backup)
                logger.info(f"Unidentified drive, skipping: {drive} (volume: {volume_name})")
                
            except Exception as e:
                logger.error(f"Error identifying drive {drive}: {e}")
                continue
        
        # Combine all Qdrive drives and create mapping
        qdrive_drives = qdrive_201_drives + qdrive_203_drives + qdrive_230_drives + qdrive_231_drives
        
        # Create Qdrive number mapping
        self.qdrive_number_mapping = {}
        logger.info(f"Auto identification results:")
        logger.info(f"  qdrive_201_drives: {qdrive_201_drives}")
        logger.info(f"  qdrive_203_drives: {qdrive_203_drives}")
        logger.info(f"  qdrive_230_drives: {qdrive_230_drives}")
        logger.info(f"  qdrive_231_drives: {qdrive_231_drives}")
        
        for drive in qdrive_201_drives:
            self.qdrive_number_mapping[drive] = '201'
        for drive in qdrive_203_drives:
            self.qdrive_number_mapping[drive] = '203'
        for drive in qdrive_230_drives:
            self.qdrive_number_mapping[drive] = '230'
        for drive in qdrive_231_drives:
            self.qdrive_number_mapping[drive] = '231'
        
        logger.info(f"Created qdrive_number_mapping: {self.qdrive_number_mapping}")
        
        self.qdrive_drives = qdrive_drives
        self.vector_drives = vector_drives
        self.transfer_drives = transfer_drives
        self.backup_drives = backup_drives
        
        # Strict drive detection - no fallback logic
        # Only drives that match specific criteria are classified
        
        # Log unclassified drives
        classified_drives = set(qdrive_drives + vector_drives + transfer_drives + backup_drives)
        unclassified_drives = [drive for drive in available_drives if drive not in classified_drives]
        
        if unclassified_drives:
            logger.info(f"Unclassified drives (will remain unassigned): {unclassified_drives}")
            for drive in unclassified_drives:
                volume_name = self._get_volume_name(drive)
                logger.info(f"  {drive} - Volume: '{volume_name}'")
        
        # Log detection results
        if not backup_drives:
            logger.info("No Echo backup drives detected (must be Echo*backup)")
        if not transfer_drives:
            logger.info("No Echo transfer drives detected (must be Echo* but not ending with backup)")
        
        logger.info(f"Drive identification completed:")
        logger.info(f"  Qdrive 201 drives: {qdrive_201_drives}")
        logger.info(f"  Qdrive 203 drives: {qdrive_203_drives}")
        logger.info(f"  Qdrive 230 drives: {qdrive_230_drives}")
        logger.info(f"  Qdrive 231 drives: {qdrive_231_drives}")
        logger.info(f"  Vector drives: {vector_drives}")
        logger.info(f"  Transfer drives: {transfer_drives}")
        logger.info(f"  Backup drives: {backup_drives}")
        
        return qdrive_drives, vector_drives, transfer_drives, backup_drives
    
    def _get_user_confirmation(self, qdrive_drives: List[str], vector_drives: List[str], 
                             transfer_drives: List[str], backup_drives: List[str]) -> Tuple[List[str], List[str], List[str], List[str]]:
        """Get user confirmation for drive identification results"""
        try:
            # Import confirmation interface - try both relative and absolute imports
            try:
                from utils.confirmation_interface import ConfirmationInterface
                from utils.directory_tree_analyzer import DirectoryTreeAnalyzer
            except ImportError:
                from data_copy_modules.utils.confirmation_interface import ConfirmationInterface
                from data_copy_modules.utils.directory_tree_analyzer import DirectoryTreeAnalyzer
            
            # Create analyzer and confirmation interface
            analyzer = DirectoryTreeAnalyzer(max_depth=3, max_items_per_level=5)
            confirmation_ui = ConfirmationInterface()
            
            # Display results and get user confirmation
            choice = confirmation_ui.display_identification_results(
                qdrive_drives, vector_drives, transfer_drives, backup_drives, analyzer, self.qdrive_number_mapping
            )
            
            # Handle user choice
            should_continue, new_qdrive, new_vector, new_transfer, new_backup = confirmation_ui.handle_user_confirmation(
                choice, self, qdrive_drives, vector_drives, transfer_drives, backup_drives)

            # After user confirms ('Y'), perform Vector duplicate check and stop if duplicates found
            if should_continue:
                try:
                    final_vector_drive = (new_vector if new_vector is not None else vector_drives)
                    if final_vector_drive:
                        # Import detector utilities lazily to avoid circular deps
                        try:
                            from core.system_detector import CrossPlatformSystemDetector
                        except ImportError:
                            from data_copy_modules.core.system_detector import CrossPlatformSystemDetector
                        _tmp_detector = CrossPlatformSystemDetector()
                        has_dup, dups = _tmp_detector.check_vector_duplicate_third_level(final_vector_drive[0])
                        if has_dup:
                            border = "*" * 70
                            print("\n" + border)
                            print("ERROR: Duplicate Vector date-time folders detected. Task has been aborted. Duplicates:")
                            for name in dups:
                                print(f"   - {name}")
                            print(border)
                            # Return empty to signal exit
                            return [], [], [], []
                        else:
                            print("\nSUCCESS: No duplicate Vector date-time folders found compared to previous logs. Proceeding.")
                except Exception as e:
                    print(f"[WARNING] Unable to perform Vector duplicate check: {e}")
                # Use the returned drive lists if they are not None, otherwise use original lists
                final_qdrive = new_qdrive if new_qdrive is not None else qdrive_drives
                final_vector = new_vector if new_vector is not None else vector_drives
                final_transfer = new_transfer if new_transfer is not None else transfer_drives
                final_backup = new_backup if new_backup is not None else backup_drives
                return final_qdrive, final_vector, final_transfer, final_backup
            elif choice == 'Q':
                # User chose to quit, return empty lists to signal exit
                return [], [], [], []
            else:
                # Recursive call for re-identification
                return self.identify_data_drives(require_confirmation=True)
                
        except ImportError as e:
            logger.warning(f"Confirmation interface not available: {e}")
            logger.info("Proceeding without user confirmation...")
            return qdrive_drives, vector_drives, transfer_drives, backup_drives
        except Exception as e:
            logger.error(f"Error in user confirmation: {e}")
            logger.info("Proceeding without user confirmation...")
            return qdrive_drives, vector_drives, transfer_drives, backup_drives 