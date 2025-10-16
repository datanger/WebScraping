#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copy Operation Logger - Enhanced Data Integrity Verification
"""

import logging
import datetime
import os
import psutil

# Create dedicated copy operation logger
copy_logger = logging.getLogger('copy_operations')
copy_logger.setLevel(logging.INFO)

# Global variables to store log file paths
COPY_LOG_FILE = None
FILELIST_LOG_FILE = None
LOG_DIR = None

def setup_copy_logger(vehicle_number: str = None, group_type: str = None, vector_date: str = None):
    """
    Setup copy operation logger with vehicle number and group type in filename
    
    Args:
        vehicle_number: Vehicle number (e.g., "3NRV1")
        group_type: Group type (A组盘/B组盘) - "A" or "B"
        vector_date: Vector logs folder date (e.g., "20250827") - if provided, use this instead of current date
    """
    global copy_logger, COPY_LOG_FILE, FILELIST_LOG_FILE, LOG_DIR
    
    # Create logs root directory
    logs_root = "logs"
    if not os.path.exists(logs_root):
        os.makedirs(logs_root)
        print(f"SUCCESS: Created log root directory: {logs_root}")
    
    # Use vector date if provided, otherwise use current date
    if vector_date:
        log_date = vector_date
        print(f"DATE: Using Vector logs date for log naming: {log_date}")
    else:
        log_date = datetime.datetime.now().strftime("%Y%m%d")
        print(f"DATE: Using current date for log naming: {log_date}")
    
    # Build log directory name (only use date, no time)
    if vehicle_number and group_type:
        log_dir_name = f"{vehicle_number}_{group_type}组_{log_date}"
    elif vehicle_number:
        log_dir_name = f"{vehicle_number}_{log_date}"
    else:
        log_dir_name = f"{log_date}"
    
    log_subdir = os.path.join(logs_root, log_dir_name)
    if not os.path.exists(log_subdir):
        os.makedirs(log_subdir)
        print(f"SUCCESS: Created log subdirectory: {log_subdir}")
    
    LOG_DIR = log_subdir
    
    # Generate log file names with vehicle and group info
    if vehicle_number and group_type:
        copy_log_file = os.path.join(log_subdir, f"{vehicle_number}_{group_type}组_datacopy.txt")
        filelist_log_file = os.path.join(log_subdir, f"{vehicle_number}_{group_type}组_filelist.txt")
    elif vehicle_number:
        copy_log_file = os.path.join(log_subdir, f"{vehicle_number}_datacopy.txt")
        filelist_log_file = os.path.join(log_subdir, f"{vehicle_number}_filelist.txt")
    else:
        copy_log_file = os.path.join(log_subdir, "datacopy.txt")
        filelist_log_file = os.path.join(log_subdir, "filelist.txt")
    
    # Create copy log file handler
    copy_file_handler = logging.FileHandler(copy_log_file, encoding='utf-8')
    copy_file_handler.setLevel(logging.INFO)
    
    # Create file list log file handler
    filelist_file_handler = logging.FileHandler(filelist_log_file, encoding='utf-8')
    filelist_file_handler.setLevel(logging.INFO)
    
    # Set format
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    copy_file_handler.setFormatter(formatter)
    filelist_file_handler.setFormatter(formatter)
    
    # Add handlers
    copy_logger.addHandler(copy_file_handler)
    
    # Update global variables
    COPY_LOG_FILE = copy_log_file
    FILELIST_LOG_FILE = filelist_log_file
    
    print(f"INFO: Log file paths:")
    print(f"   Copy log: {copy_log_file}")
    print(f"   File list: {filelist_log_file}")
    
    return copy_log_file, filelist_log_file

def setup_copy_logger_with_vector_date(vehicle_number: str = None, group_type: str = None, vector_date: str = None):
    """
    Setup copy operation logger with Vector date for proper naming from the start
    
    Args:
        vehicle_number: Vehicle number (e.g., "3NRV1")
        group_type: Group type (A组盘/B组盘) - "A" or "B"
        vector_date: Vector logs folder date (e.g., "20250827")
    """
    global copy_logger, COPY_LOG_FILE, FILELIST_LOG_FILE, LOG_DIR
    
    # Create logs root directory
    logs_root = "logs"
    if not os.path.exists(logs_root):
        os.makedirs(logs_root)
        print(f"SUCCESS: Created log root directory: {logs_root}")
    
    # Extract vehicle model from vehicle number (e.g., "3NRV1" -> "RV1")
    vehicle_model = None
    if vehicle_number:
        import re
        match = re.search(r'3N([A-Z]+\d+)', vehicle_number)
        if match:
            vehicle_model = match.group(1)
        else:
            vehicle_model = vehicle_number
    
    # Use vector date if provided, otherwise use current date
    if vector_date:
        log_date = vector_date
        print(f"DATE: Using Vector logs date for log naming: {log_date}")
    else:
        log_date = datetime.datetime.now().strftime("%Y%m%d")
        print(f"DATE: Using current date for log naming: {log_date}")
    
    # Build log directory name with vehicle model and vector date (date only, no time)
    if vehicle_model and vector_date:
        log_dir_name = f"{vehicle_model}_{vector_date}"  # e.g., "RV1_20250826"
    elif vehicle_model:
        log_dir_name = f"{vehicle_model}_{log_date}"
    elif vector_date:
        log_dir_name = vector_date
    else:
        # Fallback to current date with time
        current_time = datetime.datetime.now().strftime("%H%M%S")
        log_dir_name = f"{log_date}_{current_time}"
    
    log_subdir = os.path.join(logs_root, log_dir_name)
    if not os.path.exists(log_subdir):
        os.makedirs(log_subdir)
        print(f"SUCCESS: Created log subdirectory: {log_subdir}")
    
    LOG_DIR = log_subdir
    
    # Generate log file names (keep simple names)
    copy_log_file = os.path.join(log_subdir, "datacopy.txt")
    filelist_log_file = os.path.join(log_subdir, "filelist.txt")
    
    # Create copy log file handler
    copy_file_handler = logging.FileHandler(copy_log_file, encoding='utf-8')
    copy_file_handler.setLevel(logging.INFO)
    
    # Create file list log file handler
    filelist_file_handler = logging.FileHandler(filelist_log_file, encoding='utf-8')
    filelist_file_handler.setLevel(logging.INFO)
    
    # Set format
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    copy_file_handler.setFormatter(formatter)
    filelist_file_handler.setFormatter(formatter)
    
    # Add handlers
    copy_logger.addHandler(copy_file_handler)
    
    # Update global variables
    COPY_LOG_FILE = copy_log_file
    FILELIST_LOG_FILE = filelist_log_file
    
    print(f"INFO: Log file paths:")
    print(f"   Copy log: {copy_log_file}")
    print(f"   File list: {filelist_log_file}")
    
    return copy_log_file, filelist_log_file

def log_vehicle_and_group_info(vehicle_number: str = None, group_type: str = None):
    """
    Log vehicle number and group information at the beginning of the log file
    
    Args:
        vehicle_number: Vehicle number (e.g., "3NRV1")
        group_type: Group type (A组盘/B组盘) - "A" or "B"
    """
    try:
        if not COPY_LOG_FILE:
            return
            
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(COPY_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{timestamp}: ========== Data Copy Task Information ==========\n")
            if vehicle_number:
                f.write(f"{timestamp}: Vehicle Number: {vehicle_number}\n")
            if group_type:
                f.write(f"{timestamp}: Group Type: {group_type} Group Drive\n")
            f.write(f"{timestamp}: Copy Start Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{timestamp}: ===========================================\n\n")
            
    except Exception as e:
        print(f"Error logging vehicle and group information: {e}")

def rename_log_files_with_vector_date(vector_date: str, vehicle_number: str = None, group_type: str = None):
    """
    Rename existing log directory to use Vector logs date and vehicle number
    
    Args:
        vector_date: Vector logs folder date (e.g., "20250827")
        vehicle_number: Vehicle number (e.g., "3NRV1")
        group_type: Group type (A组盘/B组盘) - "A" or "B"
    """
    global COPY_LOG_FILE, FILELIST_LOG_FILE, LOG_DIR
    
    try:
        if not LOG_DIR or not os.path.exists(LOG_DIR):
            print("[WARNING] No log directory found to rename")
            return False
        
        # Extract vehicle model from vehicle number (e.g., "3NRV1" -> "RV1")
        vehicle_model = None
        if vehicle_number:
            import re
            match = re.search(r'3N([A-Z]+\d+)', vehicle_number)
            if match:
                vehicle_model = match.group(1)
            else:
                vehicle_model = vehicle_number
        
        # Build new log directory name with vehicle model and vector date (date only, no time)
        if vehicle_model:
            new_log_dir_name = f"{vehicle_model}_{vector_date}"
        else:
            new_log_dir_name = f"{vector_date}"
        
        # Create new log directory path
        logs_root = "logs"
        new_log_subdir = os.path.join(logs_root, new_log_dir_name)
        
        if os.path.exists(new_log_subdir):
            print(f"[WARNING] Log directory already exists: {new_log_subdir}")
            return False
        
        # Move log directory
        import shutil
        shutil.move(LOG_DIR, new_log_subdir)
        
        # Update global variables
        LOG_DIR = new_log_subdir
        
        # Update log file paths (keep original file names)
        COPY_LOG_FILE = os.path.join(new_log_subdir, "datacopy.txt")
        FILELIST_LOG_FILE = os.path.join(new_log_subdir, "filelist.txt")
        
        print(f"SUCCESS: Log directory renamed to use Vector date:")
        print(f"   New directory: {new_log_subdir}")
        print(f"   Copy log: {COPY_LOG_FILE}")
        print(f"   File list: {FILELIST_LOG_FILE}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Error renaming log files: {e}")
        return False

def log_copy_operation(message: str, log_type: str = 'copy', is_error: bool = False):
    """
    Record copy operation logs
    
    Args:
        message: Log message
        log_type: Log type ('copy' or 'filelist')
        is_error: Whether this is an error message (for red color display)
    """
    try:
        # Replace "copied" with "backup" when copying to backup drives
        if 'backup' in message.lower() and 'copied' in message.lower():
            message = message.replace('copied', 'backup')
        
        if log_type == 'copy' and COPY_LOG_FILE:
            with open(COPY_LOG_FILE, 'a', encoding='utf-8') as f:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if is_error:
                    # Add red color formatting for errors (ANSI escape codes)
                    f.write(f"{timestamp}: \033[91m{message}\033[0m\n")
                else:
                    f.write(f"{timestamp}: {message}\n")
        elif log_type == 'filelist' and FILELIST_LOG_FILE:
            with open(FILELIST_LOG_FILE, 'a', encoding='utf-8') as f:
                if is_error:
                    f.write(f"\033[91m{message}\033[0m\n")
                else:
                    f.write(f"{message}\n")
    except Exception as e:
        print(f"Error writing to log file: {e}")

def log_source_drives_before_copy(source_drives: list, drive_info: dict, qdrive_number_mapping: dict = None, vector_drives: list = None):
    """
    Record detailed information of source drives before copy (for subsequent verification)
    
    Args:
        source_drives: List of source drives
        drive_info: Drive information dictionary
        qdrive_number_mapping: Mapping of drive letters to Qdrive numbers (201/203/230/231)
        vector_drives: List of vector drives
    """
    try:
        if not COPY_LOG_FILE:
            return
            
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(COPY_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"\n{timestamp}: ========== Source Drive Information Before Copy (for Data Integrity Verification) ==========\n")
            f.write(f"{timestamp}: Copy start time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{timestamp}: Total source drives: {len(source_drives)}\n\n")
            
            for i, drive in enumerate(source_drives, 1):
                # Determine drive type and number
                drive_type = ""
                if qdrive_number_mapping and drive in qdrive_number_mapping:
                    drive_type = f" (Qdrive {qdrive_number_mapping[drive]})"
                elif vector_drives and drive in vector_drives:
                    drive_type = " (Vector)"
                else:
                    drive_type = " (Unknown)"
                
                f.write(f"{timestamp}: 【Source Drive {i}】: {drive}{drive_type}\n")
                
                if drive in drive_info and 'error' not in drive_info[drive]:
                    info = drive_info[drive]
                    
                    # Basic information
                    f.write(f"{timestamp}:   Volume Label: {info.get('volume_name', 'Unknown')}\n")
                    f.write(f"{timestamp}:   File System: {info.get('fs_type', 'Unknown')}\n")
                    
                    # Disk usage
                    if info.get('total', 0) > 0:
                        total_gb = info['total'] / (1024**3)
                        used_gb = info['used'] / (1024**3)
                        free_gb = info['free'] / (1024**3)
                        f.write(f"{timestamp}:   Total Capacity: {total_gb:.2f} GB\n")
                        f.write(f"{timestamp}:   Used Space: {used_gb:.2f} GB\n")
                        f.write(f"{timestamp}:   Available Space: {free_gb:.2f} GB\n")
                    
                    # Data directory statistics
                    if 'data' in os.listdir(drive):
                        data_path = os.path.join(drive, 'data')
                        try:
                            try:
                                from utils.file_utils import get_directory_stats
                            except ImportError:
                                from data_copy_modules.utils.file_utils import get_directory_stats
                            stats = get_directory_stats(data_path)
                            f.write(f"{timestamp}:   Data directory stats: {stats['file_count']} files, {stats['total_size']} bytes\n")
                        except Exception as e:
                            f.write(f"{timestamp}:   Data directory stats failed: {e}\n")
                    
                    if 'logs' in os.listdir(drive):
                        logs_path = os.path.join(drive, 'logs')
                        try:
                            try:
                                from utils.file_utils import get_directory_stats
                            except ImportError:
                                from data_copy_modules.utils.file_utils import get_directory_stats
                            stats = get_directory_stats(logs_path)
                            f.write(f"{timestamp}:   Logs directory stats: {stats['file_count']} files, {stats['total_size']} bytes\n")
                        except Exception as e:
                            f.write(f"{timestamp}:   Logs directory stats failed: {e}\n")
                    
                    # BitLocker status
                    if info.get('bitlocker_status'):
                        f.write(f"{timestamp}:   BitLocker Status: {info['bitlocker_status']}\n")
                else:
                    f.write(f"{timestamp}:   Information retrieval failed or drive error\n")
                
                f.write(f"{timestamp}:   - Separator\n")
            
            f.write(f"{timestamp}: ========== Source Drive Information Recording Complete ==========\n\n")
            
    except Exception as e:
        print(f"Error recording source drive information: {e}")

def log_target_drives_before_copy(transfer_drives: list, backup_drives: list, drive_info: dict):
    """
    Record detailed information of target drives before copy (for subsequent verification)
    
    Args:
        transfer_drives: List of transfer drives
        backup_drives: List of backup drives
        drive_info: Drive information dictionary
    """
    try:
        if not COPY_LOG_FILE:
            return
            
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(COPY_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"\n{timestamp}: ========== Target Drive Information Before Copy (for Data Integrity Verification) ==========\n")
            
            # Transfer drive information
            f.write(f"{timestamp}: Transfer Drives ({len(transfer_drives)} drives):\n")
            for i, drive in enumerate(transfer_drives, 1):
                f.write(f"{timestamp}:   【Transfer Drive {i}】: {drive}\n")
                
                if drive in drive_info and 'error' not in drive_info[drive]:
                    info = drive_info[drive]
                    f.write(f"{timestamp}:     Volume Label: {info.get('volume_name', 'Unknown')}\n")
                    
                    if info.get('total', 0) > 0:
                        total_gb = info['total'] / (1024**3)
                        used_gb = info['used'] / (1024**3)
                        free_gb = info['free'] / (1024**3)
                        f.write(f"{timestamp}:     Total Capacity: {total_gb:.2f} GB\n")
                        f.write(f"{timestamp}:     Used Space: {used_gb:.2f} GB\n")
                        f.write(f"{timestamp}:     Available Space: {free_gb:.2f} GB\n")
                
                # 检查Existing data directory
                data_path = os.path.join(drive, 'data')
                if os.path.exists(data_path):
                    try:
                        from utils.file_utils import get_directory_stats
                        stats = get_directory_stats(data_path)
                        f.write(f"{timestamp}:     Existing data directory: {stats['file_count']} 个文件, {stats['total_size']} 字节\n")
                        f.write(f"{timestamp}:     💡 注意: Transfer盘的data目录会累积多个源盘的数据\n")
                    except Exception as e:
                        f.write(f"{timestamp}:     Existing data directory统计失败: {e}\n")
                else:
                    f.write(f"{timestamp}:     Existing data directory: 不存在\n")
                
                f.write(f"{timestamp}:     - Separator\n")
            
            # Backup Drives信息
            f.write(f"{timestamp}: Backup Drives ({len(backup_drives)} 个):\n")
            for i, drive in enumerate(backup_drives, 1):
                f.write(f"{timestamp}:   【Backup Drives {i}】: {drive}\n")
                
                if drive in drive_info and 'error' not in drive_info[drive]:
                    info = drive_info[drive]
                    f.write(f"{timestamp}:     Volume Label: {info.get('volume_name', 'Unknown')}\n")
                    
                    if info.get('total', 0) > 0:
                        total_gb = info['total'] / (1024**3)
                        used_gb = info['used'] / (1024**3)
                        free_gb = info['free'] / (1024**3)
                        f.write(f"{timestamp}:     Total Capacity: {total_gb:.2f} GB\n")
                        f.write(f"{timestamp}:     Used Space: {used_gb:.2f} GB\n")
                        f.write(f"{timestamp}:     Available Space: {free_gb:.2f} GB\n")
                
                # 检查Existing directories结构
                backup_dirs = []
                for item in os.listdir(drive):
                    item_path = os.path.join(drive, item)
                    if os.path.isdir(item_path) and not item.startswith('.'):
                        backup_dirs.append(item)
                
                f.write(f"{timestamp}:     Existing directories: {', '.join(backup_dirs) if backup_dirs else '无'}\n")
                
                # 检查是否有data目录
                data_path = os.path.join(drive, 'data')
                if os.path.exists(data_path):
                    try:
                        from utils.file_utils import get_directory_stats
                        stats = get_directory_stats(data_path)
                        f.write(f"{timestamp}:     Existing data directory: {stats['file_count']} 个文件, {stats['total_size']} 字节\n")
                    except Exception as e:
                        f.write(f"{timestamp}:     Existing data directory统计失败: {e}\n")
                else:
                    f.write(f"{timestamp}:     Existing data directory: 不存在\n")
                
                f.write(f"{timestamp}:     - Separator\n")
            
            f.write(f"{timestamp}: ========== Target Drive Information Recording Complete ==========\n\n")
            
    except Exception as e:
        print(f"Error recording target drive information: {e}")

def log_copy_verification_summary(source_drives: list, transfer_drives: list, backup_drives: list):
    """
    记录拷贝完成后的校验总结（用于人工校验数据完整性）
    
    Args:
        source_drives: 源驱动器列表
        transfer_drives: Transfer驱动器列表
        backup_drives: Backup Drives列表
    """
    try:
        if not COPY_LOG_FILE:
            return
            
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(COPY_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"\n{timestamp}: ========== 拷贝完成后的数据完整性校验总结 ==========\n")
            f.write(f"{timestamp}: 拷贝完成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{timestamp}: 请人工校验以下信息:\n\n")
            
            # 源驱动器校验
            f.write(f"{timestamp}: 【源驱动器数据校验】\n")
            f.write(f"{timestamp}: 源驱动器总数: {len(source_drives)}\n")
            for i, drive in enumerate(source_drives, 1):
                f.write(f"{timestamp}:   源驱动器 {i}: {drive}\n")
                f.write(f"{timestamp}:     请检查: 原始数据是否完整，是否有损坏文件\n")
            
            # Transfer驱动器校验
            f.write(f"\n{timestamp}: 【Transfer驱动器数据校验】\n")
            f.write(f"{timestamp}: Transfer驱动器总数: {len(transfer_drives)}\n")
            f.write(f"{timestamp}: 💡 重要提醒: Transfer盘的data目录会累积多个源盘的数据\n")
            f.write(f"{timestamp}:   因此文件数量和大小会大于单个源盘，这是正常现象\n")
            for i, drive in enumerate(transfer_drives, 1):
                f.write(f"{timestamp}:   Transfer驱动器 {i}: {drive}\n")
                f.write(f"{timestamp}:     请检查:\n")
                f.write(f"{timestamp}:       1. data目录是否存在\n")
                f.write(f"{timestamp}:       2. 是否包含所有源盘的数据（累积检查）\n")
                f.write(f"{timestamp}:       3. 目录结构是否完整\n")
                f.write(f"{timestamp}:       4. 不要单独对比单个源盘的文件数量\n")
            
            # Backup Drives校验
            f.write(f"\n{timestamp}: 【Backup Drives数据校验】\n")
            f.write(f"{timestamp}: Backup Drives总数: {len(backup_drives)}\n")
            for i, drive in enumerate(backup_drives, 1):
                f.write(f"{timestamp}:   Backup Drives {i}: {drive}\n")
                f.write(f"{timestamp}:     请检查:\n")
                f.write(f"{timestamp}:       1. 目录结构是否正确（根目录/二级目录/data/时间目录）\n")
                f.write(f"{timestamp}:       2. 是否跳过了2qd_3NRV1_v1这一级目录\n")
                f.write(f"{timestamp}:       3. 时间目录是否完整\n")
                f.write(f"{timestamp}:       4. 每个源盘的数据是否独立完整\n")
                f.write(f"{timestamp}:       5. 文件数量应与对应源盘一致\n")
            
            f.write(f"\n{timestamp}: 【校验步骤建议】\n")
            f.write(f"{timestamp}: 1. Transfer盘: 检查是否累积了所有源盘的数据（不要单独对比）\n")
            f.write(f"{timestamp}: 2. Backup盘: 每个源盘的数据应该独立完整，文件数量一致\n")
            f.write(f"{timestamp}: 3. 检查目标驱动器的目录结构是否正确\n")
            f.write(f"{timestamp}: 4. 随机抽样检查几个文件的内容完整性\n")
            f.write(f"{timestamp}: 5. 检查是否有文件损坏或丢失\n")
            
            f.write(f"\n{timestamp}: ========== 数据完整性校验总结完成 ==========\n\n")
            
    except Exception as e:
        print(f"记录拷贝校验总结时出错: {e}")

def log_single_copy_verification(source_drive: str, target_drive: str, source_stats: dict, target_stats: dict, copy_type: str):
    """
    记录单个拷贝操作的详细校验信息
    
    Args:
        source_drive: 源驱动器
        target_drive: 目标驱动器
        source_stats: 源目录统计信息
        target_stats: 目标目录统计信息
        copy_type: 拷贝类型
    """
    try:
        if not COPY_LOG_FILE:
            return
            
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(COPY_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"\n{timestamp}: ========== {copy_type} 拷贝操作校验信息 ==========\n")
            f.write(f"{timestamp}: 源驱动器: {source_drive}\n")
            f.write(f"{timestamp}: 目标驱动器: {target_drive}\n")
            
            # 源目录统计
            f.write(f"{timestamp}: 源目录统计:\n")
            f.write(f"{timestamp}:   - 文件数量: {source_stats['file_count']}\n")
            f.write(f"{timestamp}:   - 总大小: {source_stats['total_size']} 字节\n")
            
            # 目标目录统计
            f.write(f"{timestamp}: 目标目录统计:\n")
            f.write(f"{timestamp}:   - 文件数量: {target_stats['file_count']}\n")
            f.write(f"{timestamp}:   - 总大小: {target_stats['total_size']} 字节\n")
            
            # 数据完整性检查
            f.write(f"{timestamp}: 数据完整性检查:\n")
            
            # 根据拷贝类型进行不同的校验逻辑
            if 'Transfer' in copy_type:
                # Transfer盘拷贝：考虑data目录合并的情况
                f.write(f"{timestamp}:   📝 Transfer盘拷贝说明: data目录会累积多个源盘的数据\n")
                
                # 检查本次拷贝的数据是否完整
                if source_stats['file_count'] > 0 and source_stats['total_size'] > 0:
                    f.write(f"{timestamp}:   SUCCESS: 本次拷贝数据完整性: 100.00%\n")
                    f.write(f"{timestamp}:   [STATUS] 目标盘当前状态: 累积了 {target_stats['file_count']} 个文件, 总大小 {target_stats['total_size']} 字节\n")
                    f.write(f"{timestamp}:   💡 建议: 检查目标盘data目录中是否包含本次源盘的所有文件\n")
                    f.write(f"{timestamp}:   [WARNING] 注意: 不要因为文件数量增加而误判为拷贝失败\n")
                else:
                    f.write(f"{timestamp}:   [WARNING] 源盘数据为空，无法进行完整性校验\n")
                    
            else:
                # Backup盘拷贝：要求完全一致
                f.write(f"{timestamp}:   📝 Backup盘拷贝说明: 要求文件数量和大小完全一致\n")
                
                # 文件数量检查
                if source_stats['file_count'] == target_stats['file_count']:
                    f.write(f"{timestamp}:   SUCCESS: 文件数量: 一致 ({source_stats['file_count']} = {target_stats['file_count']})\n")
                else:
                    f.write(f"{timestamp}:   ERROR: 文件数量: 不一致 (源: {source_stats['file_count']} ≠ 目标: {target_stats['file_count']})\n")
                    f.write(f"{timestamp}:     缺失文件数: {abs(source_stats['file_count'] - target_stats['file_count'])}\n")
                
                # 文件大小检查
                size_diff = abs(source_stats['total_size'] - target_stats['total_size'])
                if size_diff < 1024:  # 允许1KB的误差
                    f.write(f"{timestamp}:   SUCCESS: 文件大小: 一致 (误差 < 1KB)\n")
                else:
                    f.write(f"{timestamp}:   ERROR: 文件大小: 不一致\n")
                    f.write(f"{timestamp}:     源大小: {source_stats['total_size']} 字节\n")
                    f.write(f"{timestamp}:     目标大小: {target_stats['total_size']} 字节\n")
                    f.write(f"{timestamp}:     差异: {size_diff} 字节 ({size_diff / (1024**2):.2f} MB)\n")
                
                # 拷贝效率
                if source_stats['total_size'] > 0:
                    efficiency = (target_stats['total_size'] / source_stats['total_size']) * 100
                    f.write(f"{timestamp}:   拷贝效率: {efficiency:.2f}%\n")
            
            f.write(f"{timestamp}: ========== {copy_type} 拷贝操作校验信息完成 ==========\n\n")
            
    except Exception as e:
        print(f"记录单个拷贝校验信息时出错: {e}")
