#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core System Detector Module
"""

import os
import shutil
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple

# Import submodules
try:
    from drivers.drive_detector import DriveDetector
    from drivers.bitlocker_manager import BitlockerManager
    from data_copy.vector_data_handler import VectorDataHandler
    from data_copy.qdrive_data_handler import QdriveDataHandler
    from utils.file_utils import get_directory_stats, format_size, generate_directory_tree, copy_directory_with_rename
    from utils.progress_bar import create_progress_bar, update_progress, close_progress
    from logging_utils.copy_logger import log_copy_operation, log_source_drives_before_copy, log_target_drives_before_copy, log_copy_verification_summary, log_single_copy_verification
except ImportError:
    from data_copy_modules.drivers.drive_detector import DriveDetector
    from data_copy_modules.drivers.bitlocker_manager import BitlockerManager
    from data_copy_modules.data_copy.vector_data_handler import VectorDataHandler
    from data_copy_modules.data_copy.qdrive_data_handler import QdriveDataHandler
    from data_copy_modules.utils.file_utils import get_directory_stats, format_size, generate_directory_tree, copy_directory_with_rename
    from data_copy_modules.utils.progress_bar import create_progress_bar, update_progress, close_progress
    from data_copy_modules.logging_utils.copy_logger import log_copy_operation, log_source_drives_before_copy, log_target_drives_before_copy, log_copy_verification_summary, log_single_copy_verification

logger = logging.getLogger(__name__)

class CrossPlatformSystemDetector:
    """Cross-platform System Detector Class"""
    
    def __init__(self):
        """Initialize system detector"""
        # Create submodule instances
        self.drive_detector = DriveDetector()
        self.bitlocker_manager = BitlockerManager(self.drive_detector.os_type)
        self.vector_handler = VectorDataHandler()
        self.qdrive_handler = QdriveDataHandler()
        
        # Get operating system type
        self.os_type = self.drive_detector.os_type
        
        # Initialize other attributes (lazy initialization)
        self.drives = []
        self.system_drives = []
        self.source_drives = []
        self.destination_drives = []
        self.drive_info = {}
        self.qdrive_drives = []
        self.vector_drives = []
        self.transfer_drives = []
        self.backup_drives = []
        self.qdrive_number_mapping = {}  # Qdrive number mapping
        
        logger.info(f"Detected operating system: {self.os_type}")
    
    def detect_all_drives(self) -> List[str]:
        """Detect all available drives in the system"""
        self.drives = self.drive_detector.detect_all_drives()
        return self.drives
    
    def get_system_drives(self) -> List[str]:
        """Get system drives list"""
        self.system_drives = self.drive_detector.get_system_drives()
        return self.system_drives
    
    def classify_drives(self) -> Tuple[List[str], List[str]]:
        """Classify drives into source data drives and target backup drives"""
        source_drives, destination_drives = self.drive_detector.classify_drives()
        self.source_drives = source_drives
        self.destination_drives = destination_drives
        return source_drives, destination_drives
    
    def get_drive_information(self) -> Dict[str, Dict]:
        """Get detailed information for all drives"""
        self.drive_info = self.drive_detector.get_drive_information()
        
        # Add BitLocker status information
        if self.os_type == "windows":
            for drive in self.drive_info:
                if 'error' not in self.drive_info[drive]:
                    try:
                        self.drive_info[drive]['bitlocker_status'] = self.bitlocker_manager.check_bitlocker_status(drive)
                    except Exception as e:
                        logger.warning(f"Unable to get BitLocker status for drive {drive}: {e}")
                        self.drive_info[drive]['bitlocker_status'] = "Unknown"
        
        # Log source and target drive information
        try:
            source_drives = self.source_drives if hasattr(self, 'source_drives') else []
            transfer_drives = self.transfer_drives if hasattr(self, 'transfer_drives') else []
            backup_drives = self.backup_drives if hasattr(self, 'backup_drives') else []
            
            if source_drives:
                log_source_drives_before_copy(source_drives, self.drive_info)
            if transfer_drives or backup_drives:
                log_target_drives_before_copy(transfer_drives, backup_drives, self.drive_info)
        except Exception as e:
            logger.warning(f"Error logging drive information: {e}")
        
        return self.drive_info
    
    def unlock_all_locked_drives(self, recovery_key: str) -> Dict[str, bool]:
        """Unlock all BitLocker locked drives (Windows only)"""
        return self.bitlocker_manager.unlock_all_locked_drives(self.drive_info, recovery_key)
    
    def identify_data_drives(self, require_confirmation: bool = True) -> Tuple[List[str], List[str], List[str], List[str]]:
        """Identify Qdrive, Vector, transfer and backup drives"""
        qdrive_drives, vector_drives, transfer_drives, backup_drives = self.drive_detector.identify_data_drives(require_confirmation=require_confirmation)
        self.qdrive_drives = qdrive_drives
        self.vector_drives = vector_drives
        self.transfer_drives = transfer_drives
        self.backup_drives = backup_drives
        
        # 传递qdrive_number_mapping从drive_detector到system_detector
        if hasattr(self.drive_detector, 'qdrive_number_mapping'):
            self.qdrive_number_mapping = self.drive_detector.qdrive_number_mapping
            logger.info(f"Transferred qdrive_number_mapping: {self.qdrive_number_mapping}")
        else:
            self.qdrive_number_mapping = {}
            logger.warning("qdrive_number_mapping not found in drive_detector")
        
        # Log data drive classification information
        try:
            # Combine all source drives
            source_drives = qdrive_drives + vector_drives
            if source_drives:
                log_source_drives_before_copy(source_drives, self.drive_info, self.qdrive_number_mapping, vector_drives)
            if transfer_drives or backup_drives:
                log_target_drives_before_copy(transfer_drives, backup_drives, self.drive_info)
        except Exception as e:
            logger.warning(f"Error logging data drive classification information: {e}")
        
        return qdrive_drives, vector_drives, transfer_drives, backup_drives
    
    def check_vector_data_dates(self, vector_drive: str) -> Tuple[bool, List[str]]:
        """检查Vector数据盘中的日期数量"""
        return self.vector_handler.check_vector_data_dates(vector_drive)
    
    def extract_vehicle_model(self, vehicle_id: str) -> str:
        """从车号中提取车型"""
        return self.qdrive_handler.extract_vehicle_model(vehicle_id)
    
    def _extract_qdrive_number(self, qdrive_drive: str) -> str:
        """Extract Qdrive number (201, 203, 230, 231) from drive path"""
        import re
        if '201' in qdrive_drive:
            return '201'
        elif '203' in qdrive_drive:
            return '203'
        elif '230' in qdrive_drive:
            return '230'
        elif '231' in qdrive_drive:
            return '231'
        else:
            # Try to extract 3-digit number from path
            match = re.search(r'(\d{3})', qdrive_drive)
            if match:
                return match.group(1)
            return 'Unknown'
    
    def create_backup_directory_structure(self, backup_drive: str, qdrive_drives: List[str]) -> bool:
        """在backup盘创建Qdrive数据的目录结构"""
        return self.qdrive_handler.create_backup_directory_structure(backup_drive, qdrive_drives)
    
    def copy_qdrive_data_to_transfer(self, qdrive_drive: str, transfer_drive: str) -> bool:
        """Copy Qdrive data to transfer drive (maintain original structure)"""
        try:
            data_path = os.path.join(qdrive_drive, 'data')
            if not os.path.exists(data_path):
                logger.error(f"Qdrive data drive {qdrive_drive} does not contain data folder")
                return False
            
            # Get pre-copy statistics
            logger.info(f"Analyzing source directory {data_path}...")
            source_stats = get_directory_stats(data_path)
            logger.info(f"Source directory stats: {source_stats['file_count']} files, total size: {format_size(source_stats['total_size'])}")
            
            # Extract drive number from Qdrive path using mapping
            drive_number = self.qdrive_number_mapping.get(qdrive_drive, 'Unknown')
            
            # Record source data information to log
            log_copy_operation(f"The source path of Qdrive {drive_number} is: {os.path.dirname(data_path)}, The size of Qdrive {drive_number} to be copied is: {str(source_stats['total_size'])} bytes, and file number is {str(source_stats['file_count'])};")
            
            # Generate and record directory tree with drive information
            drive_number = self.qdrive_number_mapping.get(qdrive_drive, 'UNKNOWN')
            tree_str = f"Qdrive {drive_number} ({qdrive_drive}):\n" + generate_directory_tree(data_path)
            log_copy_operation(tree_str, 'filelist')
            
            target_data_path = os.path.join(transfer_drive, 'data')
            os.makedirs(target_data_path, exist_ok=True)
            
            # Record copy start with A/B disk info
            disk_info = ""
            if hasattr(self, 'qdrive_handler') and self.qdrive_handler and hasattr(self.qdrive_handler, 'backup_disk_type') and self.qdrive_handler.backup_disk_type:
                disk_info = f" - {self.qdrive_handler.backup_disk_type} Drive"
            log_copy_operation(f"Qdrive {drive_number} data started to copy to Transfer Drive({transfer_drive}){disk_info};")
            
            # Get the detailed progress tracker
            try:
                from utils.detailed_progress import get_progress_tracker
            except ImportError:
                from data_copy_modules.utils.detailed_progress import get_progress_tracker
            progress_tracker = get_progress_tracker()
            task_id = f"Qdrive {drive_number} → Transfer"
            
            # Update task with total files
            progress_tracker.update_task(task_id, 0, total_files=source_stats['file_count'])
            
            # Track copied files count
            copied_files_count = 0
            
            def progress_callback(increment):
                nonlocal copied_files_count
                copied_files_count += increment
                progress_tracker.update_task(task_id, copied_files_count)
            
            # Copy directory with auto-rename functionality
            success = copy_directory_with_rename(data_path, target_data_path, progress_callback)
            
            if success:
                # Get post-copy statistics
                target_stats = get_directory_stats(target_data_path)
                logger.info(f"Copy operation completed:")
                logger.info(f"  Source directory: {source_stats['file_count']} files, {format_size(source_stats['total_size'])}")
                logger.info(f"  Target directory: {target_stats['file_count']} files, {format_size(target_stats['total_size'])}")
                
                # Use the actual copied files count from progress callback, not target directory stats
                # This ensures progress bar reflects actual copy progress, not target directory contents
                final_copied_files = copied_files_count
                logger.info(f"  Actual copied files: {final_copied_files}")
                progress_tracker.update_task(task_id, final_copied_files, 'completed')
                
                # Record copy completion statistics
                log_copy_operation(f"Qdrive {drive_number} data has been copied to Transfer Drive({transfer_drive}), with data size: {str(target_stats['total_size'])} bytes, and file number is {str(target_stats['file_count'])};")
                
                # Record copy verification information (disabled to reduce log verbosity)
                # try:
                #     log_single_copy_verification(qdrive_drive, transfer_drive, source_stats, target_stats, 'Qdrive_Transfer')
                # except Exception as e:
                #     logger.warning(f"Error recording copy verification information: {e}")
                
                # Record copy success
                log_copy_operation(f"Qdrive {drive_number} data has been copied successfully;")
                
                # Notify progress tracker that task is completed
                progress_tracker.complete_task(task_id, True)
                
                return True
            else:
                logger.error(f"Failed to copy directory")
                # Notify progress tracker that task failed
                progress_tracker.complete_task(task_id, False)
                return False
            
        except Exception as e:
            logger.error(f"Error copying Qdrive data to transfer drive: {e}")
            log_copy_operation(f"Error copying Qdrive {drive_number} data: {e}", is_error=True)
            # Notify progress tracker that task failed
            progress_tracker.complete_task(task_id, False)
            return False
    
    def _copy_directory_with_progress(self, src: str, dst: str, progress_bar) -> bool:
        """带进度条的目录拷贝函数"""
        try:
            # 创建目标目录
            os.makedirs(dst, exist_ok=True)
            
            # 遍历源目录
            for root, dirs, files in os.walk(src):
                # 计算相对路径
                rel_path = os.path.relpath(root, src)
                target_dir = os.path.join(dst, rel_path)
                
                # 创建子目录
                os.makedirs(target_dir, exist_ok=True)
                
                # 拷贝文件
                for file in files:
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(target_dir, file)
                    
                    try:
                        shutil.copy2(src_file, dst_file)
                        update_progress(progress_bar, 1)
                    except Exception as e:
                        logger.warning(f"拷贝文件 {src_file} 时出错: {e}")
                        continue
            
            return True
            
        except Exception as e:
            logger.error(f"拷贝目录时出错: {e}")
            return False
    
    def _rename_vector_logs_to_archive(self, vector_drive: str) -> bool:
        """
        Rename Vector logs folder to date-archive format after copy completion
        
        Args:
            vector_drive: Vector drive path
            
        Returns:
            bool: True if rename successful, False otherwise
        """
        try:
            logs_path = os.path.join(vector_drive, 'logs')
            if not os.path.exists(logs_path):
                logger.warning(f"Vector logs folder not found at {logs_path}")
                return False
            
            # Get the creation date from files in logs folder instead of current date
            import datetime
            import time
            
            # Find the earliest creation date from files in logs folder
            earliest_date = None
            try:
                for root, dirs, files in os.walk(logs_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            # Get file creation time
                            if os.name == 'nt':  # Windows
                                creation_time = os.path.getctime(file_path)
                            else:  # Unix/Linux
                                creation_time = os.path.getmtime(file_path)
                            
                            file_date = datetime.datetime.fromtimestamp(creation_time).strftime("%Y%m%d")
                            if earliest_date is None or file_date < earliest_date:
                                earliest_date = file_date
                        except (OSError, ValueError):
                            continue
            except Exception as e:
                logger.warning(f"Could not get file dates from logs folder: {e}")
            
            # If no files found or error, use current date as fallback
            if earliest_date is None:
                earliest_date = datetime.datetime.now().strftime("%Y%m%d")
                logger.warning(f"Using current date as fallback: {earliest_date}")
            else:
                logger.info(f"Using earliest file date from logs folder: {earliest_date}")
            
            archive_name = f"{earliest_date}-archive"
            archive_path = os.path.join(vector_drive, archive_name)
            
            # Check if archive folder already exists
            if os.path.exists(archive_path):
                logger.warning(f"Archive folder {archive_path} already exists, skipping rename")
                return False
            
            # Wait a moment to ensure no other processes are using the folder
            import time
            time.sleep(2)
            
            # Rename logs folder to archive
            os.rename(logs_path, archive_path)
            logger.info(f"SUCCESS: Vector logs folder renamed: {logs_path} → {archive_path}")
            
            # Log the rename operation
            try:
                from logging_utils.copy_logger import log_copy_operation
                log_copy_operation(f"Vector Drive logs folder has been renamed to: {archive_name}")
            except ImportError:
                try:
                    from data_copy_modules.logging_utils.copy_logger import log_copy_operation
                    log_copy_operation(f"Vector Drive logs folder has been renamed to: {archive_name}")
                except Exception as e:
                    logger.warning(f"Could not log rename operation: {e}")
            except Exception as e:
                logger.warning(f"Could not log rename operation: {e}")
            
            # Return the date used for archive naming
            return earliest_date
            
        except Exception as e:
            logger.error(f"Error renaming Vector logs folder: {e}")
            return False

    def _rename_qdrive_data_to_archive(self, qdrive_drive: str, vector_drive: str = None):
        """
        Rename Qdrive 'data' folder to date-archive format after copy completion.

        The date is determined using the earliest creation time among files inside
        the 'data' folder (same logic as Vector logs rename).

        Args:
            qdrive_drive: Qdrive root path (e.g., 'J:\\')

        Returns:
            str: Date in YYYYMMDD format if rename successful, False otherwise
        """
        try:
            data_path = os.path.join(qdrive_drive, 'data')
            if not os.path.exists(data_path):
                logger.warning(f"Qdrive data folder not found at {data_path}")
                return False

            import datetime

            # Preferred: derive date from Vector third-level folder names (minimum by lexicographic order)
            derived_date = None
            if vector_drive:
                try:
                    third_level = self._get_vector_third_level_names(vector_drive)
                    if third_level:
                        min_name = sorted(third_level)[0]  # e.g., 20250818_193328
                        # Extract YYYYMMDD
                        parts = min_name.split('_')
                        if parts and len(parts[0]) == 8 and parts[0].isdigit():
                            derived_date = parts[0]
                            logger.info(f"Using earliest Vector third-level folder date for Qdrive rename: {derived_date}")
                except Exception as e:
                    logger.warning(f"Could not derive date from Vector folder names: {e}")

            # Fallback: use today's date directly (do not infer from Qdrive files)
            if not derived_date:
                derived_date = datetime.datetime.now().strftime("%Y%m%d")
                logger.warning(f"Using current date as fallback for Qdrive data rename (no Vector date): {derived_date}")

            # For Qdrive, use underscore format: YYYYMMDD_archive
            archive_name = f"{derived_date}_archive"
            archive_path = os.path.join(qdrive_drive, archive_name)

            if os.path.exists(archive_path):
                logger.warning(f"Archive folder {archive_path} already exists, skipping Qdrive data rename")
                return False

            # Ensure no other process is holding handles
            import time
            time.sleep(2)

            os.rename(data_path, archive_path)
            logger.info(f"SUCCESS: Qdrive data folder renamed: {data_path} → {archive_path}")

            # Log the rename operation
            try:
                from logging_utils.copy_logger import log_copy_operation
                log_copy_operation(f"Qdrive data folder has been renamed to: {archive_name} on {qdrive_drive}")
            except ImportError:
                try:
                    from data_copy_modules.logging_utils.copy_logger import log_copy_operation
                    log_copy_operation(f"Qdrive data folder has been renamed to: {archive_name} on {qdrive_drive}")
                except Exception as e:
                    logger.warning(f"Could not log Qdrive data rename operation: {e}")
            except Exception as e:
                logger.warning(f"Could not log Qdrive data rename operation: {e}")

            return derived_date

        except Exception as e:
            logger.error(f"Error renaming Qdrive data folder: {e}")
            return False

    def _export_vector_third_level_dirs(self, vector_drive: str) -> bool:
        """
        Export all third-level directory names under Vector logs folder to folderstructure.txt

        Structure: logs/<vehicle>/<date_time> → collect the <date_time> folder names

        The output file is written to the current application log directory (LOG_DIR)
        as folderstructure.txt, one name per line, sorted.
        """
        try:
            logs_root = os.path.join(vector_drive, 'logs')
            if not os.path.exists(logs_root):
                logger.warning(f"Vector logs folder not found at {logs_root}")
                return False

            third_level_names = []
            try:
                for vehicle_dir in os.listdir(logs_root):
                    vehicle_path = os.path.join(logs_root, vehicle_dir)
                    if not os.path.isdir(vehicle_path):
                        continue
                    try:
                        for dt_dir in os.listdir(vehicle_path):
                            dt_path = os.path.join(vehicle_path, dt_dir)
                            if os.path.isdir(dt_path):
                                third_level_names.append(dt_dir)
                    except (PermissionError, OSError):
                        continue
            except (PermissionError, OSError) as e:
                logger.warning(f"Unable to enumerate Vector logs structure: {e}")

            third_level_names = sorted(set(third_level_names))

            # Resolve LOG_DIR from copy_logger
            log_dir = None
            try:
                from logging_utils.copy_logger import LOG_DIR as APP_LOG_DIR
                log_dir = APP_LOG_DIR
            except ImportError:
                try:
                    from data_copy_modules.logging_utils.copy_logger import LOG_DIR as APP_LOG_DIR
                    log_dir = APP_LOG_DIR
                except Exception:
                    pass

            if not log_dir:
                # Fallback: use local 'logs' directory
                log_dir = os.path.join(os.getcwd(), 'logs')
                os.makedirs(log_dir, exist_ok=True)

            output_path = os.path.join(log_dir, 'folderstructure.txt')
            with open(output_path, 'w', encoding='utf-8') as f:
                for name in third_level_names:
                    f.write(f"{name}\n")

            logger.info(f"SUCCESS: Exported {len(third_level_names)} Vector third-level folders to {output_path}")

            # Log to copy log
            try:
                from logging_utils.copy_logger import log_copy_operation
                log_copy_operation(f"Exported {len(third_level_names)} Vector third-level folders to folderstructure.txt")
            except ImportError:
                try:
                    from data_copy_modules.logging_utils.copy_logger import log_copy_operation
                    log_copy_operation(f"Exported {len(third_level_names)} Vector third-level folders to folderstructure.txt")
                except Exception:
                    pass

            return True

        except Exception as e:
            logger.error(f"Error exporting Vector third-level directories: {e}")
            return False

    def _cleanup_qdrive_archives(self, qdrive_drive: str) -> Tuple[int, int]:
        """
        Remove folders under the Qdrive root whose names contain 'archive' (case-insensitive).

        Only immediate subdirectories of the Qdrive root are considered. Returns a tuple
        of (removed_count, error_count).
        """
        removed = 0
        errors = 0
        try:
            if not qdrive_drive or not os.path.isdir(qdrive_drive):
                return (0, 0)
            try:
                entries = os.listdir(qdrive_drive)
            except (PermissionError, OSError) as e:
                logger.warning(f"Unable to list Qdrive root {qdrive_drive}: {e}")
                return (0, 1)

            for name in entries:
                path = os.path.join(qdrive_drive, name)
                if os.path.isdir(path) and 'archive' in name.lower():
                    try:
                        shutil.rmtree(path, ignore_errors=False)
                        removed += 1
                        logger.info(f"Removed archive folder from Qdrive: {path}")
                        try:
                            from logging_utils.copy_logger import log_copy_operation
                            log_copy_operation(f"Removed archive folder from Qdrive: {path}")
                        except ImportError:
                            try:
                                from data_copy_modules.logging_utils.copy_logger import log_copy_operation
                                log_copy_operation(f"Removed archive folder from Qdrive: {path}")
                            except Exception:
                                pass
                    except Exception as e:
                        errors += 1
                        logger.warning(f"Failed to remove archive folder {path}: {e}")
            return (removed, errors)
        except Exception as e:
            logger.error(f"Error cleaning Qdrive archives on {qdrive_drive}: {e}")
            return (removed, errors + 1)

    def _get_vector_third_level_names(self, vector_drive: str) -> List[str]:
        """Return list of third-level folder names under Vector logs (logs/<vehicle>/<date_time>)."""
        names: List[str] = []
        logs_root = os.path.join(vector_drive, 'logs')
        if not os.path.exists(logs_root):
            return names
        try:
            for vehicle_dir in os.listdir(logs_root):
                vehicle_path = os.path.join(logs_root, vehicle_dir)
                if not os.path.isdir(vehicle_path):
                    continue
                try:
                    for dt_dir in os.listdir(vehicle_path):
                        dt_path = os.path.join(vehicle_path, dt_dir)
                        if os.path.isdir(dt_path):
                            names.append(dt_dir)
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError):
            pass
        # Deduplicate and sort
        return sorted(set(names))

    def _get_latest_logged_folderstructure(self) -> List[str]:
        """Find the most recent folderstructure.txt in logs root and return its names list."""
        candidate_roots = []
        # Prefer current LOG_DIR parent if available
        try:
            from logging_utils.copy_logger import LOG_DIR as APP_LOG_DIR
            if APP_LOG_DIR:
                candidate_roots.append(os.path.dirname(APP_LOG_DIR))
        except ImportError:
            try:
                from data_copy_modules.logging_utils.copy_logger import LOG_DIR as APP_LOG_DIR
                if APP_LOG_DIR:
                    candidate_roots.append(os.path.dirname(APP_LOG_DIR))
            except Exception:
                pass
        # Fallback common locations
        candidate_roots.extend([
            os.path.join(os.getcwd(), 'logs'),
            os.path.join(os.getcwd(), 'data_copy_modules', 'logs')
        ])
        # Deduplicate while preserving order
        seen = set(); unique_roots = []
        for r in candidate_roots:
            if r and r not in seen and os.path.isdir(r):
                seen.add(r); unique_roots.append(r)

        newest_file = None
        newest_mtime = -1.0
        for root in unique_roots:
            try:
                for sub in os.listdir(root):
                    sub_path = os.path.join(root, sub)
                    if not os.path.isdir(sub_path):
                        continue
                    fs_path = os.path.join(sub_path, 'folderstructure.txt')
                    if os.path.isfile(fs_path):
                        try:
                            mtime = os.path.getmtime(fs_path)
                            if mtime > newest_mtime:
                                newest_mtime = mtime
                                newest_file = fs_path
                        except OSError:
                            continue
            except (PermissionError, OSError):
                continue

        if not newest_file:
            return []

        try:
            with open(newest_file, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
            return sorted(set(lines))
        except Exception:
            return []

    def check_vector_duplicate_third_level(self, vector_drive: str) -> Tuple[bool, List[str]]:
        """
        Compare current Vector third-level folder names with the most recent folderstructure.txt.
        Returns (has_duplicates, duplicate_list_sorted).
        """
        current = set(self._get_vector_third_level_names(vector_drive))
        previous = set(self._get_latest_logged_folderstructure())
        duplicates = sorted(current.intersection(previous))
        return (len(duplicates) > 0, duplicates)

    def copy_vector_data_to_transfer(self, vector_drive: str, transfer_drive: str) -> bool:
        """Copy Vector data to transfer drive (maintain original structure)"""
        try:
            logs_path = os.path.join(vector_drive, 'logs')
            if not os.path.exists(logs_path):
                logger.error(f"Vector data drive {vector_drive} does not contain logs folder")
                return False
            
            # Get pre-copy statistics
            logger.info(f"Analyzing source directory {logs_path}...")
            source_stats = get_directory_stats(logs_path)
            logger.info(f"Source directory stats: {source_stats['file_count']} files, total size: {format_size(source_stats['total_size'])}")
            
            target_logs_path = os.path.join(transfer_drive, 'logs')
            os.makedirs(target_logs_path, exist_ok=True)
            
            # Generate and record directory tree with drive information
            tree_str = f"Vector Drive ({vector_drive}):\n" + generate_directory_tree(logs_path)
            log_copy_operation(tree_str, 'filelist')
            
            # Record copy start with A/B disk info
            disk_info = ""
            if hasattr(self, 'qdrive_handler') and self.qdrive_handler and hasattr(self.qdrive_handler, 'backup_disk_type'):
                disk_info = f" - {self.qdrive_handler.backup_disk_type} Drive"
            log_copy_operation(f"Vector data started to copy to Transfer Drive({transfer_drive}){disk_info};")
            
            # Get the detailed progress tracker
            try:
                from utils.detailed_progress import get_progress_tracker
            except ImportError:
                from data_copy_modules.utils.detailed_progress import get_progress_tracker
            progress_tracker = get_progress_tracker()
            task_id = "Vector → Transfer"
            
            # Update task with total files
            progress_tracker.update_task(task_id, 0, total_files=source_stats['file_count'])
            
            # Track copied files count
            copied_files_count = 0
            
            def progress_callback(increment):
                nonlocal copied_files_count
                copied_files_count += increment
                progress_tracker.update_task(task_id, copied_files_count)
            
            # 使用自动重命名功能拷贝目录
            success = copy_directory_with_rename(logs_path, target_logs_path, progress_callback)
            
            if success:
                # 获取拷贝后的统计信息
                target_stats = get_directory_stats(target_logs_path)
                logger.info(f"拷贝完成统计:")
                logger.info(f"  源目录: {source_stats['file_count']} 个文件, {format_size(source_stats['total_size'])}")
                logger.info(f"  目标目录: {target_stats['file_count']} 个文件, {format_size(target_stats['total_size'])}")
                
                # Use the actual copied files count from progress callback, not target directory stats
                final_copied_files = copied_files_count
                logger.info(f"  实际拷贝文件数: {final_copied_files}")
                progress_tracker.update_task(task_id, final_copied_files, 'completed')
                
                # 验证拷贝结果
                if source_stats['file_count'] == target_stats['file_count']:
                    logger.info(f"SUCCESS: 文件数量验证成功: {source_stats['file_count']} = {target_stats['file_count']}")
                else:
                    logger.warning(f"[WARNING] 文件数量不匹配: 源 {source_stats['file_count']} ≠ 目标 {target_stats['file_count']}")
                
                if abs(source_stats['total_size'] - target_stats['total_size']) < 1024:  # 允许1KB的误差
                    logger.info(f"SUCCESS: 文件大小验证成功: {format_size(source_stats['total_size'])} ≈ {format_size(target_stats['total_size'])}")
                else:
                    logger.warning(f"[WARNING] 文件大小不匹配: 源 {format_size(source_stats['total_size'])} ≠ 目标 {format_size(target_stats['total_size'])}")
                
                # Record copy completion statistics
                log_copy_operation(f"Vector data has been copied to Transfer Drive({transfer_drive}), with data size: {str(target_stats['total_size'])} bytes, and file number is {str(target_stats['file_count'])};")
                
                # Record copy success
                log_copy_operation(f"Vector data has been copied successfully;")
            else:
                logger.error(f"ERROR: Vector data copy to Transfer drive failed")
            
            # Notify progress tracker that task is completed
            progress_tracker.complete_task(task_id, success)
            
            # Note: Vector logs folder renaming will be handled after all copy tasks complete
            # to avoid conflicts with other threads that might still be accessing the folder
            
            return success
            
        except Exception as e:
            logger.error(f"Error copying Vector data to Transfer drive: {e}")
            # Notify progress tracker that task failed
            progress_tracker.complete_task(task_id, False)
            return False
    
    def copy_vector_data_to_backup(self, vector_drive: str, backup_drive: str, target_dir: str = None) -> bool:
        """Copy Vector data to backup drive (maintain original structure)"""
        try:
            logs_path = os.path.join(vector_drive, 'logs')
            if not os.path.exists(logs_path):
                logger.error(f"Vector data drive {vector_drive} does not contain logs folder")
                return False
            
            # Get source directory statistics
            logger.info(f"Analyzing source directory {logs_path}...")
            source_stats = get_directory_stats(logs_path)
            logger.info(f"Source directory stats: {source_stats['file_count']} files, total size: {format_size(source_stats['total_size'])}")
            
            # If target directory is specified, use it; otherwise copy directly to backup drive root
            if target_dir:
                target_logs_path = target_dir
                logger.info(f"Using specified target directory: {target_logs_path}")
            else:
                # Fix: Copy directly to backup drive root instead of creating logs subdirectory
                target_logs_path = backup_drive
                logger.info(f"Using backup drive root as target: {target_logs_path}")
            
            os.makedirs(target_logs_path, exist_ok=True)
            
            # Generate and record directory tree with drive information
            tree_str = f"Vector Drive ({vector_drive}):\n" + generate_directory_tree(logs_path)
            log_copy_operation(tree_str, 'filelist')
            
            # Record copy start with A/B disk info
            disk_info = ""
            if hasattr(self, 'qdrive_handler') and self.qdrive_handler and hasattr(self.qdrive_handler, 'backup_disk_type') and self.qdrive_handler.backup_disk_type:
                disk_info = f" - {self.qdrive_handler.backup_disk_type} Drive"
            log_copy_operation(f"Vector data started to backup to Backup Drive({backup_drive}){disk_info};")
            
            # Get the detailed progress tracker
            try:
                from utils.detailed_progress import get_progress_tracker
            except ImportError:
                from data_copy_modules.utils.detailed_progress import get_progress_tracker
            progress_tracker = get_progress_tracker()
            task_id = "Vector → Backup"
            
            # Update task with total files
            progress_tracker.update_task(task_id, 0, total_files=source_stats['file_count'])
            
            # Track copied files count
            copied_files_count = 0
            
            def progress_callback(increment):
                nonlocal copied_files_count
                copied_files_count += increment
                progress_tracker.update_task(task_id, copied_files_count)
            
            # Copy directory with auto-rename functionality
            success = copy_directory_with_rename(logs_path, target_logs_path, progress_callback)
            
            if success:
                # Get post-copy statistics
                target_stats = get_directory_stats(target_logs_path)
                logger.info(f"Copy operation completed:")
                logger.info(f"  Source directory: {source_stats['file_count']} files, {format_size(source_stats['total_size'])}")
                logger.info(f"  Target directory: {target_stats['file_count']} files, {format_size(target_stats['total_size'])}")
                
                # Use the actual copied files count from progress callback, not target directory stats
                final_copied_files = copied_files_count
                logger.info(f"  Actual copied files: {final_copied_files}")
                progress_tracker.update_task(task_id, final_copied_files, 'completed')
                
                # Verify copy results
                if source_stats['file_count'] == target_stats['file_count']:
                    logger.info(f"SUCCESS: File count verification successful: {source_stats['file_count']} = {target_stats['file_count']}")
                else:
                    logger.warning(f"[WARNING] File count mismatch: source {source_stats['file_count']} ≠ target {target_stats['file_count']}")
                
                if abs(source_stats['total_size'] - target_stats['total_size']) < 1024:  # Allow 1KB tolerance
                    logger.info(f"SUCCESS: File size verification successful: {format_size(source_stats['total_size'])} ≈ {format_size(target_stats['total_size'])}")
                else:
                    logger.warning(f"[WARNING] File size mismatch: source {format_size(source_stats['total_size'])} ≠ target {format_size(target_stats['total_size'])}")
                
                # Record copy completion statistics
                log_copy_operation(f"Vector data has been backup to Backup Drive({backup_drive}), with data size: {str(target_stats['total_size'])} bytes, and file number is {str(target_stats['file_count'])};")
                
                # Record copy success
                log_copy_operation(f"Vector data has been backup successfully;")
            else:
                logger.error(f"ERROR: Vector data copy to Backup drive failed")
            
            # Notify progress tracker that task is completed
            progress_tracker.complete_task(task_id, success)
            
            # Note: Vector logs folder renaming will be handled after all copy tasks complete
            # to avoid conflicts with other threads that might still be accessing the folder
            
            return success
            
        except Exception as e:
            logger.error(f"Error copying Vector data to backup drive: {e}")
            # Notify progress tracker that task failed
            progress_tracker.complete_task(task_id, False)
            return False
    
    def copy_qdrive_data_to_backup(self, qdrive_drive: str, backup_drive: str, qdrive_handler=None, drive_number=None) -> bool:
        """Copy Qdrive data to backup drive (with new directory structure)"""
        try:
            data_path = os.path.join(qdrive_drive, 'data')
            if not os.path.exists(data_path):
                logger.error(f"Qdrive data drive {qdrive_drive} does not contain data folder")
                return False
            
            # Get pre-copy statistics
            logger.info(f"Analyzing source directory {data_path}...")
            source_stats = get_directory_stats(data_path)
            logger.info(f"Source directory stats: {source_stats['file_count']} files, total size: {format_size(source_stats['total_size'])}")
            
            # Generate and record directory tree with drive information
            tree_str = f"Qdrive {drive_number} ({qdrive_drive}):\n" + generate_directory_tree(data_path)
            log_copy_operation(tree_str, 'filelist')
            
            # Record copy start information
            log_copy_operation(f"The source path of Qdrive {drive_number} is: {os.path.dirname(data_path)}, The size of Qdrive {drive_number} to be backup is: {str(source_stats['total_size'])} bytes, and file number is {str(source_stats['file_count'])};")
            
            # Use QdriveDataHandler saved directory information first
            if qdrive_handler and qdrive_handler.backup_root_dir and os.path.exists(qdrive_handler.backup_root_dir):
                root_path = qdrive_handler.backup_root_dir
                logger.info(f"Using QdriveDataHandler saved root directory: {root_path}")
            else:
                # Find root directory in backup drive
                root_dirs = [d for d in os.listdir(backup_drive) 
                            if os.path.isdir(os.path.join(backup_drive, d)) 
                            and not d.startswith('.')]
                
                if not root_dirs:
                    logger.error("No root directory found in backup drive, please create directory structure first")
                    return False
                
                # Use the latest root directory
                root_dir = sorted(root_dirs)[-1]
                root_path = os.path.join(backup_drive, root_dir)
                logger.info(f"Using detected root directory: {root_path}")
            
            # Use provided drive number first, if not available extract from drive path
            if not drive_number:
                if '201' in qdrive_drive:
                    drive_number = '201'
                elif '203' in qdrive_drive:
                    drive_number = '203'
                elif '230' in qdrive_drive:
                    drive_number = '230'
                elif '231' in qdrive_drive:
                    drive_number = '231'
                else:
                    # Try to extract number from path
                    import re
                    match = re.search(r'(\d{3})', qdrive_drive)
                    if match:
                        drive_number = match.group(1)
            
            if not drive_number:
                logger.error(f"Cannot extract drive number from drive path {qdrive_drive}")
                return False
            
            # Find corresponding secondary directory
            target_subdir = None
            for subdir in os.listdir(root_path):
                if drive_number in subdir:
                    target_subdir = subdir
                    break
            
            if not target_subdir:
                logger.error(f"Secondary directory containing drive number {drive_number} not found in root directory {os.path.basename(root_path)}")
                return False
            
            # Create data folder under secondary directory
            target_data_path = os.path.join(root_path, target_subdir, 'data')
            os.makedirs(target_data_path, exist_ok=True)
            
            # Record copy start with A/B disk info
            disk_info = ""
            if qdrive_handler and hasattr(qdrive_handler, 'backup_disk_type') and qdrive_handler.backup_disk_type:
                disk_info = f" - {qdrive_handler.backup_disk_type} Drive"
            log_copy_operation(f"Qdrive {drive_number} data started to backup to Backup Drive({backup_drive}){disk_info};")
            
            # Get the detailed progress tracker
            try:
                from utils.detailed_progress import get_progress_tracker
            except ImportError:
                from data_copy_modules.utils.detailed_progress import get_progress_tracker
            progress_tracker = get_progress_tracker()
            task_id = f"Qdrive {drive_number} → Backup"
            
            # Update task with total files
            progress_tracker.update_task(task_id, 0, total_files=source_stats['file_count'])
            
            # 使用统一的拷贝函数和进度回调
            copied_files_count = 0
            
            def progress_callback(increment):
                nonlocal copied_files_count
                copied_files_count += increment
                progress_tracker.update_task(task_id, copied_files_count)
            
            # 使用统一的拷贝函数，保持与其他函数一致
            success = copy_directory_with_rename(data_path, target_data_path, progress_callback)
            
            if success:
                # 获取拷贝后的统计信息
                target_stats = get_directory_stats(target_data_path)
                logger.info(f"拷贝完成统计:")
                logger.info(f"  源目录: {source_stats['file_count']} 个文件, {format_size(source_stats['total_size'])}")
                logger.info(f"  目标目录: {target_stats['file_count']} 个文件, {format_size(target_stats['total_size'])}")
                
                # Use the actual copied files count from progress callback, not target directory stats
                final_copied_files = copied_files_count
                logger.info(f"  实际拷贝文件数: {final_copied_files}")
                progress_tracker.update_task(task_id, final_copied_files, 'completed')
                
                # 验证拷贝结果
                if source_stats['file_count'] == target_stats['file_count']:
                    logger.info(f"SUCCESS: 文件数量验证成功: {source_stats['file_count']} = {target_stats['file_count']}")
                else:
                    logger.warning(f"[WARNING] 文件数量验证: 源 {source_stats['file_count']} ≠ 目标 {target_stats['file_count']}")
                
                if abs(source_stats['total_size'] - target_stats['total_size']) < 1024:  # 允许1KB的误差
                    logger.info(f"SUCCESS: 文件大小验证成功: {format_size(source_stats['total_size'])} ≈ {format_size(target_stats['total_size'])}")
                else:
                    logger.warning(f"[WARNING] 文件大小验证: 源 {format_size(source_stats['total_size'])} ≈ 目标 {format_size(target_stats['total_size'])}")
                
                # 记录拷贝校验信息
                # Record copy verification information (disabled to reduce log verbosity)
                # try:
                #     log_single_copy_verification(qdrive_drive, backup_drive, source_stats, target_stats, 'Qdrive_Backup')
                # except Exception as e:
                #     logger.warning(f"记录拷贝校验信息时出错: {e}")
                
                logger.info(f"SUCCESS: Successfully backup {final_copied_files} files to {target_data_path}")
                
                # Record copy completion statistics
                log_copy_operation(f"Qdrive {drive_number} data has been backup to Backup Drive({backup_drive}), with data size: {str(target_stats['total_size'])} bytes, and file number is {str(target_stats['file_count'])};")
                
                # Record copy success
                log_copy_operation(f"Qdrive {drive_number} data has been backup successfully;")
            
            # Notify progress tracker that task is completed
            progress_tracker.complete_task(task_id, success)
            
            return success
            
        except Exception as e:
            logger.error(f"Error copying Qdrive data to Backup drive: {e}")
            # Notify progress tracker that task failed
            progress_tracker.complete_task(task_id, False)
            return False
    
    def execute_data_copy_plan(self) -> bool:
        """执行完整的数据拷贝计划"""
        try:
            logger.info("开始执行数据拷贝计划")
            
            # 1. 识别所有驱动器
            qdrive_drives, vector_drives, transfer_drives, backup_drives = self.identify_data_drives()
            
            if not qdrive_drives and not vector_drives:
                logger.error("未找到任何数据源盘")
                return False
            
            if not transfer_drives and not backup_drives:
                logger.error("未找到任何目标盘")
                return False
            
            # 2. 检查Vector数据日期
            for vector_drive in vector_drives:
                is_single_date, dates = self.check_vector_data_dates(vector_drive)
                if is_single_date:
                    print(f"\nVector drive {vector_drive} contains a single date dataset: {dates[0]}")
                    confirm = input("Confirm copy this data? (y/n): ").lower().strip()
                    if confirm != 'y':
                        logger.info(f"User cancelled copying Vector data drive {vector_drive}")
                        vector_drives.remove(vector_drive)
                else:
                    print(f"\nVector drive {vector_drive} contains multiple date datasets: {dates}")
                    print("Copy paused. Please handle this case manually.")
                    vector_drives.remove(vector_drive)
            
            # 3. 拷贝到transfer盘（并行处理）
            if transfer_drives:
                logger.info("Starting parallel data copy to Transfer drive")
                transfer_drive = transfer_drives[0]  # 使用第一个transfer盘
                
                # 并行拷贝Qdrive数据
                if qdrive_drives:
                    logger.info(f"Parallel copying {len(qdrive_drives)} Qdrive data drives to Transfer drive")
                    self._parallel_copy_qdrive_to_transfer(qdrive_drives, transfer_drive)
                
                # 并行拷贝Vector数据
                if vector_drives:
                    logger.info(f"Parallel copying {len(vector_drives)} Vector data drives to Transfer drive")
                    self._parallel_copy_vector_to_transfer(vector_drives, transfer_drive)
            
            # 4. 拷贝到backup盘（并行处理）
            if backup_drives:
                logger.info("Starting parallel data copy to Backup drive")
                backup_drive = backup_drives[0]  # 使用第一个backup盘
                
                # 并行拷贝Vector数据（保持原始结构）
                if vector_drives:
                    logger.info(f"Parallel copying {len(vector_drives)} Vector data drives to Backup drive")
                    self._parallel_copy_vector_to_backup(vector_drives, backup_drive)
                
                # 创建Qdrive数据的目录结构
                if qdrive_drives:
                    if self.create_backup_directory_structure(backup_drive, qdrive_drives):
                        # 并行拷贝Qdrive数据到新目录结构
                        logger.info(f"Parallel copying {len(qdrive_drives)} Qdrive data drives to Backup drive")
                        self._parallel_copy_qdrive_to_backup(qdrive_drives, backup_drive)
            
            logger.info("Data copy plan execution completed")
            return True
            
        except Exception as e:
            logger.error(f"Error executing data copy plan: {e}")
            return False
    
    def _parallel_copy_qdrive_to_transfer(self, qdrive_drives: List[str], transfer_drive: str):
        """Parallel copy Qdrive data to Transfer drive"""
        try:
            with ThreadPoolExecutor(max_workers=min(len(qdrive_drives), 4)) as executor:
                # 提交所有拷贝任务
                future_to_drive = {
                    executor.submit(self.copy_qdrive_data_to_transfer, drive, transfer_drive): drive
                    for drive in qdrive_drives
                }
                
                # 等待所有任务完成
                for future in as_completed(future_to_drive):
                    drive = future_to_drive[future]
                    try:
                        success = future.result()
                        if success:
                            logger.info(f"SUCCESS: Successfully copied Qdrive data drive {drive} to Transfer drive")
                        else:
                            logger.error(f"ERROR: Failed to copy Qdrive data drive {drive} to Transfer drive")
                    except Exception as e:
                        logger.error(f"ERROR: Error copying Qdrive data drive {drive}: {e}")
                        
        except Exception as e:
            logger.error(f"Error in parallel copy of Qdrive data to Transfer drive: {e}")
    
    def _parallel_copy_vector_to_transfer(self, vector_drives: List[str], transfer_drive: str):
        """Parallel copy Vector data to Transfer drive"""
        try:
            with ThreadPoolExecutor(max_workers=min(len(vector_drives), 4)) as executor:
                # 提交所有拷贝任务
                future_to_drive = {
                    executor.submit(self.copy_vector_data_to_transfer, drive, transfer_drive): drive
                    for drive in vector_drives
                }
                
                # 等待所有任务完成
                for future in as_completed(future_to_drive):
                    drive = future_to_drive[future]
                    try:
                        success = future.result()
                        if success:
                            logger.info(f"SUCCESS: Successfully copied Vector data drive {drive} to Transfer drive")
                        else:
                            logger.error(f"ERROR: Failed to copy Vector data drive {drive} to Transfer drive")
                    except Exception as e:
                        logger.error(f"ERROR: Error copying Vector data drive {drive}: {e}")
                        
        except Exception as e:
            logger.error(f"Error in parallel copy of Vector data to Transfer drive: {e}")
    
    def _parallel_copy_vector_to_backup(self, vector_drives: List[str], backup_drive: str):
        """Parallel copy Vector data to Backup drive"""
        try:
            with ThreadPoolExecutor(max_workers=min(len(vector_drives), 4)) as executor:
                # 提交所有拷贝任务
                future_to_drive = {
                    executor.submit(self.copy_vector_data_to_backup, drive, backup_drive): drive
                    for drive in vector_drives
                }
                
                # 等待所有任务完成
                for future in as_completed(future_to_drive):
                    drive = future_to_drive[future]
                    try:
                        success = future.result()
                        if success:
                            logger.info(f"SUCCESS: Successfully copied Vector data drive {drive} to Backup drive")
                        else:
                            logger.error(f"ERROR: Failed to copy Vector data drive {drive} to Backup drive")
                    except Exception as e:
                        logger.error(f"ERROR: Error copying Vector data drive {drive}: {e}")
                        
        except Exception as e:
            logger.error(f"Error in parallel copy of Vector data to Backup drive: {e}")
    
    def _parallel_copy_qdrive_to_backup(self, qdrive_drives: List[str], backup_drive: str):
        """Parallel copy Qdrive data to Backup drive"""
        try:
            with ThreadPoolExecutor(max_workers=min(len(qdrive_drives), 4)) as executor:
                # 提交所有拷贝任务
                future_to_drive = {
                    executor.submit(self.copy_qdrive_data_to_backup, drive, backup_drive): drive
                    for drive in qdrive_drives
                }
                
                # 等待所有任务完成
                for future in as_completed(future_to_drive):
                    drive = future_to_drive[future]
                    try:
                        success = future.result()
                        if success:
                            logger.info(f"SUCCESS: Successfully copied Qdrive data drive {drive} to Backup drive")
                        else:
                            logger.error(f"ERROR: Failed to copy Qdrive data drive {drive} to Backup drive")
                    except Exception as e:
                        logger.error(f"ERROR: Error copying Qdrive data drive {drive}: {e}")
                        
        except Exception as e:
            logger.error(f"Error in parallel copy of Qdrive data to Backup drive: {e}")
    
    def print_summary(self):
        """打印系统检测摘要"""
        print("\n" + "="*60)
        print("Cross-platform system detection and data copy summary")
        print("="*60)
        
        print(f"\nOS: {self.os_type}")
        print(f"Total drives: {len(self.drives)}")
        print(f"System drives: {len(self.system_drives)}")
        print(f"Source data drives: {len(self.source_drives)}")
        print(f"Destination backup drives: {len(self.destination_drives)}")
        
        print(f"\nData drive identification:")
        print(f"  Qdrive data drives: {len(self.qdrive_drives)}")
        print(f"  Vector data drives: {len(self.vector_drives)}")
        print(f"  Transfer target drives: {len(self.transfer_drives)}")
        print(f"  Backup target drives: {len(self.backup_drives)}")
        
        print("\nDrive details:")
        print("-" * 60)
        
        for drive, info in self.drive_info.items():
            if 'error' not in info:
                total_gb = info['total'] / (1024**3)
                used_gb = info['used'] / (1024**3)
                free_gb = info['free'] / (1024**3)
                
                print(f"\nDrive: {drive}")
                print(f"  Volume label: {info['volume_name']}")
                print(f"  File system: {info['fs_type']}")
                print(f"  Total capacity: {total_gb:.2f} GB")
                print(f"  Used space: {used_gb:.2f} GB")
                print(f"  Available space: {free_gb:.2f} GB")
                if self.os_type == "windows":
                    print(f"  BitLocker status: {info.get('bitlocker_status', 'Unknown')}")
                print(f"  Type: ", end="")
                
                if info['is_system']:
                    print("System", end=" ")
                if info['is_source']:
                    print("Source", end=" ")
                if info['is_destination']:
                    print("Backup destination", end=" ")
                print()
            else:
                print(f"\nDrive: {drive}")
                print(f"  Error: {info['error']}")
        
        # 记录拷贝完成后的校验总结到日志
        try:
            source_drives = self.qdrive_drives + self.vector_drives
            log_copy_verification_summary(source_drives, self.transfer_drives, self.backup_drives)
        except Exception as e:
            logger.warning(f"记录拷贝校验总结到日志时出错: {e}")
        
        print("\n" + "="*60) 