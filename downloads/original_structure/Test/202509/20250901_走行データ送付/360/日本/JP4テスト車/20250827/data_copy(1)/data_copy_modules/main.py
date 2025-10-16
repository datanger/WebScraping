#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据拷贝工具主程序
Data Copy Tool Main Program
"""

import logging
import os
try:
    from core.system_detector import CrossPlatformSystemDetector
    from logging_utils.copy_logger import setup_copy_logger
except ImportError:
    from data_copy_modules.core.system_detector import CrossPlatformSystemDetector
    from data_copy_modules.logging_utils.copy_logger import setup_copy_logger

# Configure logs
def setup_main_logger():
    """Setup main program logger"""
    # Create logs root directory
    logs_root = "logs"
    if not os.path.exists(logs_root):
        os.makedirs(logs_root)
    
    # Create subdirectory named by run time
    import datetime
    run_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_subdir = os.path.join(logs_root, run_time)
    if not os.path.exists(log_subdir):
        os.makedirs(log_subdir)
    
    # Configure logging
    system_log_file = os.path.join(log_subdir, "system_detector.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(system_log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_main_logger()

def main():
    """Main function - Demonstrate cross-platform system detection and data copy functionality"""
    print("Cross-Platform System Detection and Data Copy Tool")
    print("=" * 50)
    
    # Setup copy log logger (basic initialization)
    copy_log_file, filelist_log_file = setup_copy_logger()
    print(f"Copy log file: {copy_log_file}")
    print(f"File list log file: {filelist_log_file}")
    
    # Create system detector instance
    detector = CrossPlatformSystemDetector()
    
    try:
        # 1. Detect all drives
        print("\n1. Detecting all available drives...")
        drives = detector.detect_all_drives()
        
        if not drives:
            print("No drives detected, program exiting")
            return
        
        # 2. Get system drives
        print("\n2. Identifying system drives...")
        system_drives = detector.get_system_drives()
        
        # 3. Classify drives
        print("\n3. Classifying drives...")
        source_drives, destination_drives = detector.classify_drives()
        
        # 4. Get detailed drive information
        print("\n4. Getting detailed drive information...")
        drive_info = detector.get_drive_information()
        
        # 5. Check BitLocker status (Windows only)
        if detector.os_type == "windows":
            print("\n5. Checking BitLocker status...")
            locked_drives = [drive for drive, info in drive_info.items() 
                            if info.get('bitlocker_status') == 'Locked']
            
            if locked_drives:
                print(f"BitLocker locked drives found: {locked_drives}")
                print("\nUnlocking BitLocker-encrypted drives...")
                
                # 直接使用密码解锁所有驱动器
                unlock_results = detector.unlock_all_locked_drives(drive_info)
                
                if unlock_results:
                    print("\nUnlock results:")
                    for drive, success in unlock_results.items():
                        status = "Success" if success else "Failed"
                        print(f"  {drive}: {status}")
                else:
                    print("Unlock operation cancelled or failed")
            else:
                print("No BitLocker locked drives found")
        else:
            print("\n5. Skipping BitLocker check (non-Windows system)")
        
        # 6. Identify data drives
        print("\n6. Identifying data drives...")
        detector.identify_data_drives()
        
        # 7. Ask whether to execute copy plan
        print("\n7. Drive identification completed")
        response = input("Execute data copy plan? (y/n): ").lower().strip()
        
        if response == 'y':
            print("\nExecuting data copy plan...")
            success = detector.execute_data_copy_plan()
            if success:
                print("Data copy plan completed")
            else:
                print("Data copy plan failed")
        else:
            print("Skip data copy step")
        
        # 8. Print summary
        detector.print_summary()
        
    except KeyboardInterrupt:
        print("\n\nUser cancelled the operation")
    except Exception as e:
        print(f"\nProgram error: {e}")
        logger.error(f"Program error: {e}", exc_info=True)
    finally:
        print("\nProgram completed")
        # Prevent auto-close of console window in packaged exe
        try:
            input("\nPress Enter to exit...")
        except (EOFError, KeyboardInterrupt):
            pass

if __name__ == "__main__":
    main() 