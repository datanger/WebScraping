#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive Data Copy Tool Main Program
"""

import os
import logging
import getpass
import sys
import time
from typing import List, Dict, Tuple
try:
    from core.system_detector import CrossPlatformSystemDetector
    from data_copy.qdrive_data_handler import QdriveDataHandler
    from logging_utils.copy_logger import setup_copy_logger
    from config_manager import get_config_manager
except ImportError:
    from data_copy_modules.core.system_detector import CrossPlatformSystemDetector
    from data_copy_modules.data_copy.qdrive_data_handler import QdriveDataHandler
    from data_copy_modules.logging_utils.copy_logger import setup_copy_logger
    from data_copy_modules.config_manager import get_config_manager

# Configure logging - will be initialized later with vehicle and group info
copy_log_file = None
filelist_log_file = None
logger = logging.getLogger('copy_operations')

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

class InteractiveDataCopyTool:
    """Interactive Data Copy Tool Class"""
    
    def __init__(self):
        """Initialize tool"""
        self.detector = CrossPlatformSystemDetector()
        self.config_manager = get_config_manager()
        self.qdrive_drives = []  # User selected Qdrive drives
        self.vector_drive = None  # User selected Vector drive
        self.transfer_drive = None  # User selected transfer drive
        self.backup_drive = None  # User selected backup drive
        self.copy_plan = {}  # Copy plan
        self.qdrive_number_mapping = {}  # Qdrive number mapping
        
    def show_all_drives(self) -> List[str]:
        """Show all external drives list - optimized version to avoid repeated scanning"""
        print("\n" + "="*60)
        print("Detected External Drives:")
        print("="*60)
        
        drives = self.detector.detect_all_drives()
        if not drives:
            print("ERROR: No drives detected")
            return []
        
        # Filter out system drives, only show external drives
        system_drives = self.detector.get_system_drives()
        external_drives = [drive for drive in drives if drive not in system_drives]
        
        if not external_drives:
            print("ERROR: No external drives detected")
            return []
        
        # Get all drive information at once to avoid repeated calls
        drive_info = self.detector.get_drive_information()
        
        # Display drive information
        for i, drive in enumerate(external_drives, 1):
            try:
                info = drive_info.get(drive, {})
                if 'error' not in info:
                    # Check if it's an encrypted drive
                    if info.get('is_encrypted', False):
                        bitlocker_status = info.get('bitlocker_status', 'Unknown')
                        if bitlocker_status == 'Locked':
                            print(f"{i:2d}. {drive} - [LOCKED] BitLocker encrypted drive (locked, needs unlock)")
                        elif bitlocker_status == 'Unlocked':
                            print(f"{i:2d}. {drive} - [UNLOCKED] BitLocker encrypted drive (unlocked)")
                        else:
                            print(f"{i:2d}. {drive} - 🔐 BitLocker encrypted drive (status: {bitlocker_status})")
                    elif not info.get('is_accessible', True):
                        print(f"{i:2d}. {drive} - [WARNING] Access restricted")
                    else:
                        total_gb = info.get('total', 0) / (1024**3)
                        free_gb = info.get('free', 0) / (1024**3)
                        volume_name = info.get('volume_name', 'Unknown')
                        print(f"{i:2d}. {drive} - {volume_name} - Total: {total_gb:.2f}GB - Free: {free_gb:.2f}GB")
                else:
                    print(f"{i:2d}. {drive} - Error: {info['error']}")
            except Exception as e:
                # Check if it's an encrypted drive
                try:
                    # Try to access the drive
                    os.listdir(drive)
                    print(f"{i:2d}. {drive} - Status normal")
                except (PermissionError, OSError):
                    print(f"{i:2d}. {drive} - [LOCKED] Encrypted drive (needs unlock)")
                except Exception as e2:
                    print(f"{i:2d}. {drive} - Unable to get info: {e2}")
        
        return external_drives
    
    def select_qdrive_drives(self, external_drives: List[str]) -> List[str]:
        """Manually select Qdrive drives (201, 203, 230, 231) - optimized version to avoid repeated scanning"""
        print("\n" + "="*60)
        print("Please select Qdrive data drives (201, 203, 230, 231):")
        print("="*60)
        print("Please select one by one, enter drive letter or full path, enter 'done' to finish selection")
        
        selected_drives = []
        expected_numbers = ['201', '203', '230', '231']
        
        # Get drive information at once to avoid repeated calls
        drive_info = self.detector.get_drive_information()
        
        # Create mapping from drive number to drive
        drive_number_mapping = {}
        
        while len(selected_drives) < 4:
            # Calculate remaining drive numbers to select
            remaining_numbers = []
            for num in expected_numbers:
                # Check if this drive number has already been assigned to a drive
                if num not in drive_number_mapping.values():
                    remaining_numbers.append(num)
            
            print(f"\nCurrently selected: {selected_drives}")
            print(f"Still need to select: {remaining_numbers}")
            
            # Show available drive list (using already obtained information)
            print("\nAvailable drive list:")
            available_drives = [drive for drive in external_drives if drive not in selected_drives]
            for i, drive in enumerate(available_drives, 1):
                try:
                    info = drive_info.get(drive, {})
                    if 'error' not in info:
                        total_gb = info.get('total', 0) / (1024**3)
                        free_gb = info.get('free', 0) / (1024**3)
                        volume_name = info.get('volume_name', 'Unknown')
                        print(f"  {i:2d}. {drive} - {volume_name} - Total: {total_gb:.2f}GB - Available: {free_gb:.2f}GB")
                    else:
                        print(f"  {i:2d}. {drive} - Error: {info['error']}")
                except Exception as e:
                    print(f"  {i:2d}. {drive} - Unable to get info: {e}")
            
            # Prompt user to select specific Qdrive number
            if remaining_numbers:
                next_number = remaining_numbers[0]
                choice = input(f"\nSelect Qdrive {next_number} (enter number or 'done' to finish): ").strip()
            else:
                choice = input(f"\nSelect Qdrive (enter number or 'done' to finish): ").strip()
            
            if choice.lower() == 'done':
                if len(selected_drives) < 4:
                    print(f"[WARNING] Warning: Only selected {len(selected_drives)} drives, recommend selecting 4 drives")
                    confirm = input("Continue? (y/n): ").lower().strip()
                    if confirm != 'y':
                        continue
                break
            
            # Handle numeric selection
            selected_drive = None
            if choice.isdigit():
                choice_num = int(choice)
                if 1 <= choice_num <= len(available_drives):
                    selected_drive = available_drives[choice_num - 1]
                else:
                    print(f"ERROR: Invalid number: {choice_num}, please enter a number between 1-{len(available_drives)}")
                    continue
            else:
                # Direct drive letter input case
                if choice in external_drives:
                    selected_drive = choice
                else:
                    print(f"ERROR: Invalid selection: {choice}, please enter a number or correct drive letter")
                    continue
            
            # Validate selection (quick validation, no deep scanning)
            if selected_drive:
                # Quick check if contains data folder or volume name contains expected numbers
                try:
                    # Method 1: Check if volume name contains expected numbers
                    volume_name = drive_info.get(selected_drive, {}).get('volume_name', '').lower()
                    has_expected_number = any(num in volume_name for num in expected_numbers)
                    
                    # Method 2: Quick check for data folder in root directory (no deep scanning)
                    has_data_folder = False
                    try:
                        if os.access(selected_drive, os.R_OK):
                            entries = os.listdir(selected_drive)
                            has_data_folder = 'data' in entries
                    except (PermissionError, OSError):
                        # Permission error, might be encrypted drive, judge by volume name
                        pass
                    if has_expected_number or has_data_folder:
                        if selected_drive not in selected_drives:
                            # Determine the drive number for this drive
                            drive_number = None
                            for num in expected_numbers:
                                if num in volume_name.lower() or (has_data_folder and num not in [d for d in drive_number_mapping.values()]):
                                    if num not in [d for d in drive_number_mapping.values()]:
                                        drive_number = num
                                        break
                            
                            if drive_number:
                                drive_number_mapping[selected_drive] = drive_number
                                selected_drives.append(selected_drive)
                                print(f"SUCCESS: Selected Qdrive {drive_number}: {selected_drive}")
                            else:
                                print(f"[WARNING] Cannot determine drive number for {selected_drive}")
                                confirm = input("Still select this drive? (y/n): ").lower().strip()
                                if confirm == 'y':
                                    selected_drives.append(selected_drive)
                                    print(f"SUCCESS: Selected Qdrive: {selected_drive}")
                        else:
                            print(f"[WARNING] Drive already selected: {selected_drive}")
                    else:
                        print(f"[WARNING] Warning: {selected_drive} may not be a Qdrive data drive")
                        confirm = input("Still select this drive? (y/n): ").lower().strip()
                        if confirm == 'y':
                            if selected_drive not in selected_drives:
                                selected_drives.append(selected_drive)
                                print(f"SUCCESS: Selected Qdrive: {selected_drive}")
                            else:
                                print(f"[WARNING] Drive already selected: {selected_drive}")
                        else:
                            print(f"Deselected: {selected_drive}")
                            
                except Exception as e:
                    print(f"Error validating drive: {e}")
                    # If validation fails, still allow selection
                    if selected_drive not in selected_drives:
                        selected_drives.append(selected_drive)
                        print(f"SUCCESS: Selected Qdrive: {selected_drive} (validation skipped)")
                    else:
                        print(f"[WARNING] Drive already selected: {selected_drive}")
        
        self.qdrive_drives = selected_drives
        self.qdrive_number_mapping = drive_number_mapping  # Save drive number mapping
        print(f"\nSUCCESS: Qdrive drive selection completed:")
        for drive, number in drive_number_mapping.items():
            print(f"  Qdrive {number}: {drive}")
        return selected_drives
    
    def select_vector_drive(self, external_drives: List[str]) -> str:
        """Manually select Vector drive (single selection)"""
        print("\n" + "="*60)
        print("Please select Vector data drive:")
        print("="*60)
        print("Note: Vector drive should contain logs folder with structure: logs/vehicle_id/date_time")
        
        # Display available drive list
        available_drives = [drive for drive in external_drives if drive not in self.qdrive_drives]
        print("\nAvailable drives:")
        for i, drive in enumerate(available_drives, 1):
            try:
                drive_info = self.detector.get_drive_information().get(drive, {})
                if 'error' not in drive_info:
                    total_gb = drive_info.get('total', 0) / (1024**3)
                    free_gb = drive_info.get('free', 0) / (1024**3)
                    volume_name = drive_info.get('volume_name', 'Unknown')
                    print(f"  {i:2d}. {drive} - {volume_name} - Total: {total_gb:.2f}GB - Available: {free_gb:.2f}GB")
                else:
                    print(f"  {i:2d}. {drive} - Error: {drive_info['error']}")
            except Exception as e:
                print(f"  {i:2d}. {drive} - Unable to get info: {e}")
        
        while True:
            choice = input("\nPlease enter Vector drive letter or full path (enter number): ").strip()
            
            # Handle numeric selection
            selected_drive = None
            if choice.isdigit():
                choice_num = int(choice)
                if 1 <= choice_num <= len(available_drives):
                    selected_drive = available_drives[choice_num - 1]
                else:
                    print(f"ERROR: Invalid number: {choice_num}, please enter a number between 1-{len(available_drives)}")
                    continue
            else:
                # Direct drive letter input case
                if choice in external_drives:
                    selected_drive = choice
                else:
                    print(f"ERROR: Invalid selection: {choice}, please enter a number or correct drive letter")
                    continue
            
            if selected_drive:
                # Check if logs folder exists
                logs_path = os.path.join(selected_drive, 'logs')
                if os.path.exists(logs_path):
                    # Validate vehicle model
                    detected_model = self._detect_vehicle_model_from_vector(selected_drive)
                    validation_message = self.config_manager.get_vehicle_validation_message(detected_model)
                    
                    if self.config_manager.validate_vehicle_model(detected_model):
                        print(f"SUCCESS: Selected Vector drive: {selected_drive}")
                        print(f"SUCCESS: {validation_message}")
                        self.vector_drive = selected_drive
                        return selected_drive
                    else:
                        print(f"ERROR: {validation_message}")
                        print(f"ERROR: Copy operation will be aborted due to vehicle model mismatch!")
                        return None
                else:
                    print(f"ERROR: logs folder not found in {selected_drive}, please select again")
    
    def select_transfer_drive(self, external_drives: List[str]) -> str:
        """Manually select transfer drive (single selection)"""
        print("\n" + "="*60)
        print("Please select transfer target drive:")
        print("="*60)
        print("Note: Transfer drive is used to receive Qdrive and Vector data with original structure")
        
        # Display available drive list
        available_drives = [drive for drive in external_drives 
                          if drive not in self.qdrive_drives and drive != self.vector_drive]
        print("\nAvailable drive list:")
        for i, drive in enumerate(available_drives, 1):
            try:
                drive_info = self.detector.get_drive_information().get(drive, {})
                if 'error' not in drive_info:
                    total_gb = drive_info.get('total', 0) / (1024**3)
                    free_gb = drive_info.get('free', 0) / (1024**3)
                    volume_name = drive_info.get('volume_name', 'Unknown')
                    print(f"  {i:2d}. {drive} - {volume_name} - Total: {total_gb:.2f}GB - Available: {free_gb:.2f}GB")
                else:
                    print(f"  {i:2d}. {drive} - Error: {drive_info['error']}")
            except Exception as e:
                print(f"  {i:2d}. {drive} - Unable to get info: {e}")
        
        while True:
            choice = input("\nPlease enter transfer drive letter or full path (enter number, or 'q' to quit): ").strip()
            
            # Handle quit option
            if choice.lower() == 'q':
                print("Transfer drive selection cancelled")
                return None
            
            # Handle numeric selection
            selected_drive = None
            if choice.isdigit():
                choice_num = int(choice)
                if 1 <= choice_num <= len(available_drives):
                    selected_drive = available_drives[choice_num - 1]
                else:
                    print(f"ERROR: Invalid number: {choice_num}, please enter a number between 1-{len(available_drives)}")
                    continue
            else:
                # Direct drive letter input case
                if choice in external_drives:
                    selected_drive = choice
                else:
                    print(f"ERROR: Invalid selection: {choice}, please enter a number or correct drive letter")
                    continue
            
            if selected_drive:
                if selected_drive not in self.qdrive_drives and selected_drive != self.vector_drive:
                    self.transfer_drive = selected_drive
                    print(f"SUCCESS: Transfer drive selected: {selected_drive}")
                    return selected_drive
                else:
                    print(f"ERROR: {selected_drive} has been selected as data source drive, cannot be used as target drive")
    
    def select_backup_drive(self, external_drives: List[str]) -> str:
        """Manually select backup drive (single selection)"""
        print("\n" + "="*60)
        print("Please select backup target drive:")
        print("="*60)
        print("Note: Backup drive is used to receive Qdrive and Vector data, Qdrive data will be reorganized")
        
        # Display available drive list
        available_drives = [drive for drive in external_drives 
                          if drive not in self.qdrive_drives and drive != self.vector_drive and drive != self.transfer_drive]
        print("\nAvailable drive list:")
        for i, drive in enumerate(available_drives, 1):
            try:
                drive_info = self.detector.get_drive_information().get(drive, {})
                if 'error' not in drive_info:
                    total_gb = drive_info.get('total', 0) / (1024**3)
                    free_gb = drive_info.get('free', 0) / (1024**3)
                    volume_name = drive_info.get('volume_name', 'Unknown')
                    print(f"  {i:2d}. {drive} - {total_gb:.2f}GB - Available: {free_gb:.2f}GB")
                else:
                    print(f"  {i:2d}. {drive} - Error: {drive_info['error']}")
            except Exception as e:
                print(f"  {i:2d}. {drive} - Unable to get info: {e}")
        
        while True:
            choice = input("\nPlease enter backup drive letter or full path (enter number, or 'q' to quit): ").strip()
            
            # Handle quit option
            if choice.lower() == 'q':
                print("Backup drive selection cancelled")
                return None
            
            # Handle numeric selection
            selected_drive = None
            if choice.isdigit():
                choice_num = int(choice)
                if 1 <= choice_num <= len(available_drives):
                    selected_drive = available_drives[choice_num - 1]
                else:
                    print(f"ERROR: Invalid number: {choice_num}, please enter a number between 1-{len(available_drives)}")
                    continue
            else:
                # Direct drive letter input case
                if choice in external_drives:
                    selected_drive = choice
                else:
                    print(f"ERROR: Invalid selection: {choice}, please enter a number or correct drive letter")
                    continue
            
            if selected_drive:
                if selected_drive not in self.qdrive_drives and selected_drive != self.vector_drive and selected_drive != self.transfer_drive:
                    self.backup_drive = selected_drive
                    print(f"SUCCESS: Backup drive selected: {selected_drive}")
                    return selected_drive
                else:
                    print(f"ERROR: {selected_drive} has been selected, cannot be selected again")
    
    def create_copy_plan(self) -> Dict:
        """Manually decide copy plan"""
        print("\n" + "="*60)
        print("Please decide on copy plan:")
        print("="*60)
        
        copy_plan = {
            'qdrive_to_transfer': False,
            'vector_to_transfer': False,
            'vector_to_backup': False,
            'qdrive_to_backup': False
        }
        
        print("[PLAN] Copy Plan Selection:")
        print("="*60)
        
        # Display current drive status for debugging
        print(f"CHECKING: Current Drive Status:")
        print(f"   Qdrive drives: {self.qdrive_drives}")
        print(f"   Vector drive: {self.vector_drive}")
        print(f"   Transfer drive: {self.transfer_drive}")
        print(f"   Backup drive: {self.backup_drive}")
        print("="*60)
        
        # 1. Transfer drive copy selection
        print("PROCESSING: Transfer Drive Copy Operation:")
        print("   Copy Qdrive and Vector data to Transfer drive, maintaining original directory structure")
        
        # Check if Transfer drive exists
        logger.info(f"Transfer drive status when creating copy plan: {self.transfer_drive}")
        if not self.transfer_drive:
            print("[WARNING] No Transfer drive detected. Transfer drive copy will be skipped.")
            print("ERROR: Skip Transfer drive copy")
            copy_plan['qdrive_to_transfer'] = False
            copy_plan['vector_to_transfer'] = False
        else:
            print(f"INFO: Transfer drive detected: {self.transfer_drive}")
            while True:
                choice = input("Execute Transfer drive copy? (y/n): ").lower().strip()
                if choice in ['y', 'n']:
                    if choice == 'y':
                        copy_plan['qdrive_to_transfer'] = True
                        copy_plan['vector_to_transfer'] = True
                        print("SUCCESS: Transfer drive copy selected: Qdrive + Vector data")
                    else:
                        print("ERROR: Skip Transfer drive copy")
                    break
                else:
                    print("Please enter y or n")
        
        print()
        
        # 2. Backup drive copy selection
        print("[BACKUP] Backup Drive Copy Operation:")
        print("   Reorganize Qdrive data directory structure + Vector data maintains original structure")
        
        # Check if Backup drive exists
        if not self.backup_drive:
            print("[WARNING] No Backup drive detected. Backup drive copy will be skipped.")
            print("ERROR: Skip Backup drive copy")
            copy_plan['qdrive_to_backup'] = False
            copy_plan['vector_to_backup'] = False
        else:
            print(f"INFO: Backup drive detected: {self.backup_drive}")
            while True:
                choice = input("Execute Backup drive copy? (y/n): ").lower().strip()
                if choice in ['y', 'n']:
                    if choice == 'y':
                        copy_plan['qdrive_to_backup'] = True
                        copy_plan['vector_to_backup'] = True
                        print("SUCCESS: Backup drive copy selected: Qdrive(reorganized) + Vector(original structure)")
                    else:
                        print("ERROR: Skip Backup drive copy")
                    break
                else:
                    print("Please enter y or n")
        
        self.copy_plan = copy_plan
        
        # Display final copy plan
        print("\n" + "="*60)
        print("[PLAN] Final Copy Plan:")
        print("="*60)
        if copy_plan['qdrive_to_transfer'] or copy_plan['vector_to_transfer']:
            print("PROCESSING: Transfer Drive Copy:")
            if copy_plan['qdrive_to_transfer']:
                print("   SUCCESS: Qdrive data → Transfer drive (maintain original structure)")
            if copy_plan['vector_to_transfer']:
                print("   SUCCESS: Vector data → Transfer drive (maintain original structure)")
        else:
            print("ERROR: Transfer Drive Copy: Skipped")
            
        if copy_plan['qdrive_to_backup'] or copy_plan['vector_to_backup']:
            print("[BACKUP] Backup Drive Copy:")
            if copy_plan['qdrive_to_backup']:
                print("   SUCCESS: Qdrive data → Backup drive (reorganize directory structure)")
            if copy_plan['vector_to_backup']:
                print("   SUCCESS: Vector data → Backup drive (maintain original structure)")
        else:
            print("ERROR: Backup Drive Copy: Skipped")
        
        return copy_plan
    
    def handle_bitlocker_unlock(self, external_drives: List[str]) -> bool:
        """Handle BitLocker unlock (manual confirmation of decryption key)"""
        if self.detector.os_type != "windows":
            print("\nSkipping BitLocker check (non-Windows system)")
            return True
        
        print("\n" + "="*60)
        print("BitLocker Status Check:")
        print("="*60)
        
        # Get drive information, including encryption status
        drive_info = self.detector.get_drive_information()
        
        # Check all external drives
        locked_drives = []
        encrypted_drives = []
        
        for drive in external_drives:
            try:
                info = drive_info.get(drive, {})
                if info.get('is_encrypted', False):
                    encrypted_drives.append(drive)
                    bitlocker_status = info.get('bitlocker_status', 'Unknown')
                    
                    if bitlocker_status == 'Locked':
                        locked_drives.append(drive)
                        print(f"[LOCKED] {drive}: BitLocker encrypted drive (locked)")
                    elif bitlocker_status == 'Unlocked':
                        print(f"[UNLOCKED] {drive}: BitLocker encrypted drive (unlocked)")
                    else:
                        print(f"🔐 {drive}: BitLocker encrypted drive (status: {bitlocker_status})")
                else:
                    # Try using traditional method to check
                    try:
                        status = self.detector.bitlocker_manager.check_bitlocker_status(drive)
                        if status == 'Locked':
                            locked_drives.append(drive)
                            print(f"[LOCKED] {drive}: BitLocker locked")
                        else:
                            print(f"[UNLOCKED] {drive}: BitLocker status normal")
                    except Exception as e:
                        print(f"[UNKNOWN] {drive}: Unable to check BitLocker status: {e}")
            except Exception as e:
                print(f"[UNKNOWN] {drive}: Unable to check drive status: {e}")
        
        # Additional check: if drive detector identifies as encrypted but status check fails, force mark as locked
        for drive in external_drives:
            try:
                info = drive_info.get(drive, {})
                if info.get('is_encrypted', False) and drive not in locked_drives:
                    # If drive is identified as encrypted but not in locked list, force mark as locked
                    if drive not in locked_drives:
                        locked_drives.append(drive)
                        print(f"[LOCKED] {drive}: BitLocker encrypted drive (force marked as locked)")
            except Exception:
                pass
        
        if not encrypted_drives:
            print("SUCCESS: No BitLocker encrypted drives found")
            return True
        
        if not locked_drives:
            print("SUCCESS: All BitLocker encrypted drives are unlocked")
            return True
        
        print(f"\nFound {len(locked_drives)} BitLocker locked encrypted drives:")
        for drive in locked_drives:
            print(f"  - {drive}")
        
        print("\n[WARNING]  Warning: These drives are BitLocker encrypted and locked, cannot access their content")
        print("You have the following options:")
        print("1. Unlock drives (requires BitLocker password)")
        print("2. Skip these drives, continue with other available drives")
        print("3. Exit program")
        
        while True:
            choice = input("\nPlease select operation (1/2/3): ").strip()
            
            if choice == '1':
                # User chooses to unlock drives
                print("\nPlease enter BitLocker password to unlock drives")
                password = get_password_with_asterisks("Please enter BitLocker password: ").strip()
                
                if not password:
                    print("ERROR: Password cannot be empty")
                    continue
                
                print(f"\nAttempting to unlock {len(locked_drives)} drives...")
                
                try:
                    # Use password to unlock all locked drives
                    unlock_results = {}
                    for drive in locked_drives:
                        print(f"\nUnlocking drive {drive}...")
                        success = self.detector.bitlocker_manager._unlock_with_password(drive, password)
                        unlock_results[drive] = success
                        if success:
                            print(f"SUCCESS: {drive} unlocked successfully")
                        else:
                            print(f"ERROR: {drive} unlock failed")
                    
                    if unlock_results:
                        print("\nUnlock results summary:")
                        success_count = sum(unlock_results.values())
                        for drive, success in unlock_results.items():
                            status = "SUCCESS: Success" if success else "ERROR: Failed"
                            print(f"  {drive}: {status}")
                        
                        print(f"\nUnlock completed: {success_count}/{len(locked_drives)} drives successfully unlocked")
                        
                        if success_count == len(locked_drives):
                            print("SUCCESS: All BitLocker encrypted drives unlocked successfully")
                            return True
                        elif success_count > 0:
                            print("[WARNING] Some drives unlocked successfully, can continue")
                            confirm = input("Continue? (y/n): ").lower().strip()
                            return confirm == 'y'
                        else:
                            print("ERROR: All drives unlock failed")
                            retry = input("Retry? (y/n): ").lower().strip()
                            if retry == 'y':
                                continue
                            else:
                                return False
                    else:
                        print("ERROR: Unlock operation failed")
                        return False
                        
                except Exception as e:
                    print(f"ERROR: Error during unlock process: {e}")
                    retry = input("Retry? (y/n): ").lower().strip()
                    if retry == 'y':
                        continue
                    else:
                        return False
                        
            elif choice == '2':
                # User chooses to skip encrypted drives
                print("[WARNING] You chose to skip encrypted drives")
                print("Note: Skipping encrypted drives means data in them cannot be accessed")
                confirm = input("Confirm skip? (y/n): ").lower().strip()
                if confirm == 'y':
                    print("SUCCESS: Skipped encrypted drives, continuing with other available drives")
                    return True
                else:
                    continue
                    
            elif choice == '3':
                # User chooses to exit
                print("ERROR: User chose to exit program")
                return False
                
            else:
                print("ERROR: Invalid choice, please enter 1, 2, or 3")
    
    def _detect_vehicle_model_from_vector(self, vector_drive: str) -> str:
        """
        Detect vehicle model from Vector drive logs directory structure
        
        Args:
            vector_drive: Vector drive path
            
        Returns:
            str: Detected vehicle model (e.g., "RV1", "RV2") or "UNKNOWN"
        """
        try:
            logs_path = os.path.join(vector_drive, 'logs')
            if not os.path.exists(logs_path):
                return "UNKNOWN"
            
            # Look for vehicle model in logs subdirectories
            for item in os.listdir(logs_path):
                item_path = os.path.join(logs_path, item)
                if os.path.isdir(item_path):
                    # Extract vehicle model from directory name (e.g., "3NRV1" -> "RV1")
                    import re
                    match = re.search(r'(\d*RV\d+)', item.upper())
                    if match:
                        vehicle_code = match.group(1)
                        # Extract just the RV part (e.g., "3NRV1" -> "RV1")
                        rv_match = re.search(r'(RV\d+)', vehicle_code)
                        if rv_match:
                            return rv_match.group(1)
            
            return "UNKNOWN"
            
        except Exception as e:
            print(f"Warning: Could not detect vehicle model from Vector drive: {e}")
            return "UNKNOWN"
    
    def _get_vector_logs_date(self, vector_drive: str) -> str:
        """
        Get the creation date of Vector logs folder itself
        
        Args:
            vector_drive: Vector drive path
            
        Returns:
            str: Date in YYYYMMDD format, or None if not found
        """
        try:
            logs_path = os.path.join(vector_drive, 'logs')
            
            if not os.path.exists(logs_path):
                return None
            
            import datetime
            
            try:
                # Get the creation time of the logs folder itself
                if os.name == 'nt':  # Windows
                    creation_time = os.path.getctime(logs_path)
                else:  # Unix/Linux
                    creation_time = os.path.getmtime(logs_path)
                
                folder_date = datetime.datetime.fromtimestamp(creation_time).strftime("%Y%m%d")
                return folder_date
                
            except (OSError, ValueError):
                return None
            
        except Exception:
            return None
    
    def _initialize_logging(self):
        """Initialize logging with vehicle and group information"""
        global copy_log_file, filelist_log_file
        
        try:
            # Extract vehicle number from Qdrive drives
            vehicle_number = None
            group_type = None
            vector_date = None
            
            # Get Vector logs date if Vector drive exists (for log naming)
            if self.vector_drive:
                vector_date = self._get_vector_logs_date(self.vector_drive)
            
            # Try to get vehicle number from Qdrive drives
            if self.qdrive_drives:
                for drive in self.qdrive_drives:
                    data_path = os.path.join(drive, 'data')
                    if os.path.exists(data_path):
                        try:
                            # Look for vehicle directories
                            for item in os.listdir(data_path):
                                if os.path.isdir(os.path.join(data_path, item)) and '3N' in item:
                                    # Extract vehicle number from directory name like "2qd_3NRV1_v1"
                                    import re
                                    match = re.search(r'3N([A-Z]+\d+)', item)
                                    if match:
                                        vehicle_number = f"3N{match.group(1)}"
                                        break
                            if vehicle_number:
                                break
                        except Exception as e:
                            print(f"Warning: Could not extract vehicle number from {drive}: {e}")
                            continue
            
            # Try to get group type from backup drive operations
            if self.copy_plan.get('qdrive_to_backup', False) and hasattr(self, 'qdrive_handler'):
                # This will be set when backup directory structure is created
                pass
            
            # Initialize logging with Vector date for proper naming
            try:
                from data_copy_modules.logging_utils.copy_logger import setup_copy_logger_with_vector_date
                copy_log_file, filelist_log_file = setup_copy_logger_with_vector_date(vehicle_number, group_type, vector_date)
            except ImportError:
                # Fallback to relative import
                from logging_utils.copy_logger import setup_copy_logger_with_vector_date
                copy_log_file, filelist_log_file = setup_copy_logger_with_vector_date(vehicle_number, group_type, vector_date)
            
            # Log vehicle and group information
            try:
                from data_copy_modules.logging_utils.copy_logger import log_vehicle_and_group_info
                log_vehicle_and_group_info(vehicle_number, group_type)
            except ImportError:
                # Fallback to relative import
                from logging_utils.copy_logger import log_vehicle_and_group_info
                log_vehicle_and_group_info(vehicle_number, group_type)
            
            print(f"INFO: Log files initialized:")
            print(f"   Copy log: {copy_log_file}")
            print(f"   File list: {filelist_log_file}")
            
        except Exception as e:
            print(f"Warning: Could not initialize logging with vehicle info: {e}")
            # Fallback to basic logging
            copy_log_file, filelist_log_file = setup_copy_logger()

    def execute_copy_plan(self) -> bool:
        """Execute copy plan"""
        print("\n" + "="*60)
        print("Start executing data copy plan:")
        print("="*60)
        
        # Initialize logging with vehicle and group information
        self._initialize_logging()
        
        # Use high-performance mode by default
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        if cpu_count >= 8:
            max_workers = 6
        elif cpu_count >= 4:
            max_workers = 4
        else:
            max_workers = 2
        chunk_size = 32768  # 32KB
        buffer_size = 32768
        print(f"SUCCESS: High-performance mode - {max_workers} threads parallel copy")
        
        try:
            # Step 1: Create backup directory structure first (if backup operations are selected)
            if self.copy_plan['qdrive_to_backup'] or self.copy_plan['vector_to_backup']:
                print(f"\nINFO: Step 1: Creating backup directory structure first...")
                
                # Create QdriveDataHandler instance (if backup operations are needed)
                qdrive_handler = None
                logger.info(f"Qdrive backup conditions:")
                logger.info(f"   copy_plan['qdrive_to_backup']: {self.copy_plan['qdrive_to_backup']}")
                logger.info(f"   qdrive_drives: {self.qdrive_drives}")
                logger.info(f"   backup_drive: {self.backup_drive}")
                
                if self.copy_plan['qdrive_to_backup'] and self.qdrive_drives and self.backup_drive:
                    print("PROCESSING: Creating Qdrive data backup directory structure...")
                    qdrive_handler = QdriveDataHandler()
                    if not qdrive_handler.create_backup_directory_structure(self.backup_drive, self.qdrive_drives):
                        print(f"ERROR: Failed to create Backup drive directory structure")
                        return False
                    print("SUCCESS: Qdrive backup directory structure created successfully")
                else:
                    print("[WARNING] Qdrive backup conditions not met, skipping directory structure creation")
                
                # If Vector data copy to backup drive is selected, also need to pre-create logs directory
                if self.copy_plan['vector_to_backup'] and self.vector_drive and self.backup_drive:
                    print("PROCESSING: Creating Vector data backup directory structure...")
                    try:
                        # If Qdrive backup directory structure is created, use the same root directory
                        if qdrive_handler and qdrive_handler.backup_root_dir:
                            vector_target_dir = os.path.join(qdrive_handler.backup_root_dir, "logs")
                        else:
                            # If no Qdrive backup directory, create logs folder in backup drive root
                            vector_target_dir = os.path.join(self.backup_drive, "logs")
                        
                        # Ensure logs directory exists
                        os.makedirs(vector_target_dir, exist_ok=True)
                        print(f"SUCCESS: Vector backup directory structure created: {vector_target_dir}")
                    except Exception as e:
                        print(f"ERROR: Failed to create Vector backup directory structure: {e}")
                        return False
                
                print("SUCCESS: Backup drive directory structure created successfully")
            else:
                print(f"\nINFO: Step 1: No need to create backup directory structure (no backup operations selected)")
            
            # Step 2: Execute all copy tasks in parallel
            print(f"\nINFO: Step 2: Starting parallel data copy (backup directory structure ready)...")
            
            import threading
            import time
            
            # Import detailed progress tracker
            try:
                from utils.detailed_progress import get_progress_tracker
            except ImportError:
                from data_copy_modules.utils.detailed_progress import get_progress_tracker
            
            # Initialize progress tracker with configuration settings
            perf_settings = self.config_manager.get_performance_settings()
            progress_tracker = get_progress_tracker(refresh_interval=perf_settings['update_interval'])
            
            # Store results of all copy tasks
            copy_results = {}
            copy_threads = []
            
            # 1. Qdrive data → Transfer drive
            print(f"CHECKING: Transfer drive copy condition check:")
            print(f"   copy_plan['qdrive_to_transfer']: {self.copy_plan['qdrive_to_transfer']}")
            print(f"   qdrive_drives: {self.qdrive_drives}")
            print(f"   transfer_drive: {self.transfer_drive}")
            
            if self.copy_plan['qdrive_to_transfer'] and self.qdrive_drives and self.transfer_drive:
                print(f"SUCCESS: Starting Qdrive to Transfer drive copy task...")
                for qdrive_drive in self.qdrive_drives:
                    # Extract drive number for display using the same mapping as backup tasks
                    drive_number = self.qdrive_number_mapping.get(qdrive_drive, 'Unknown')
                    task_id = f"Qdrive {drive_number} → Transfer"
                    
                    # Add task to progress tracker (only for 201, 203, 230, 231)
                    if drive_number in ['201', '203', '230', '231']:
                        progress_tracker.add_task(task_id, qdrive_drive, self.transfer_drive)
                    
                    def copy_qdrive_to_transfer(drive=qdrive_drive, task_id=task_id):
                        try:
                            success = self.detector.copy_qdrive_data_to_transfer(drive, self.transfer_drive)
                            copy_results[f"qdrive_{drive}_to_transfer"] = success
                            if success:
                                pass
                            else:
                                print(f"ERROR: {drive} → {self.transfer_drive} copy failed")
                        except Exception as e:
                            copy_results[f"qdrive_{drive}_to_transfer"] = False
                            print(f"ERROR: {drive} → {self.transfer_drive} copy error: {e}")
                    
                    thread = threading.Thread(target=copy_qdrive_to_transfer)
                    copy_threads.append(thread)
                    thread.start()
            
            # 2. Vector data → Transfer drive
            print(f"CHECKING: Vector to Transfer drive copy condition check:")
            print(f"   copy_plan['vector_to_transfer']: {self.copy_plan['vector_to_transfer']}")
            print(f"   vector_drive: {self.vector_drive}")
            print(f"   transfer_drive: {self.transfer_drive}")
            
            if self.copy_plan['vector_to_transfer'] and self.vector_drive and self.transfer_drive:
                print(f"SUCCESS: Starting Vector to Transfer drive copy task...")
                task_id = "Vector → Transfer"
                progress_tracker.add_task(task_id, self.vector_drive, self.transfer_drive)
                
                def copy_vector_to_transfer():
                    try:
                        success = self.detector.copy_vector_data_to_transfer(self.vector_drive, self.transfer_drive)
                        copy_results["vector_to_transfer"] = success
                        if success:
                            pass
                        else:
                            print(f"ERROR: {self.vector_drive} → {self.transfer_drive} copy failed")
                    except Exception as e:
                        copy_results["vector_to_transfer"] = False
                        print(f"ERROR: {self.vector_drive} → {self.transfer_drive} copy error: {e}")
                
                thread = threading.Thread(target=copy_vector_to_transfer)
                copy_threads.append(thread)
                thread.start()
            
            # 3. Vector data → Backup drive
            if self.copy_plan['vector_to_backup'] and self.vector_drive and self.backup_drive:
                print(f"Starting Vector to Backup drive copy task...")
                task_id = "Vector → Backup"
                progress_tracker.add_task(task_id, self.vector_drive, self.backup_drive)
                
                def copy_vector_to_backup():
                    try:
                        # If Qdrive backup directory structure is created, use the same root directory
                        if qdrive_handler and qdrive_handler.backup_root_dir:
                            # Create logs folder directly in root directory
                            vector_target_dir = os.path.join(qdrive_handler.backup_root_dir, "logs")
                            success = self.detector.copy_vector_data_to_backup(self.vector_drive, self.backup_drive, vector_target_dir)
                        else:
                            # If no Qdrive backup directory, use default backup drive
                            success = self.detector.copy_vector_data_to_backup(self.vector_drive, self.backup_drive)
                        
                        copy_results["vector_to_backup"] = success
                        if success:
                            pass
                        else:
                            print(f"ERROR: Vector data copy failed")
                    except Exception as e:
                        copy_results["vector_to_backup"] = False
                        print(f"ERROR: Vector data copy error: {e}")
                
                thread = threading.Thread(target=copy_vector_to_backup)
                copy_threads.append(thread)
                thread.start()
            
            # Before starting Qdrive copy tasks, cleanup existing archive folders on Qdrive roots
            if self.qdrive_drives:
                print("\n🧹 Cleaning up existing 'archive' folders on Qdrive sources...")
                for qdrive_drive in self.qdrive_drives:
                    try:
                        removed, errors = self.detector._cleanup_qdrive_archives(qdrive_drive)
                        print(f"   {qdrive_drive}: removed {removed} archive folder(s), errors: {errors}")
                    except Exception as e:
                        print(f"   {qdrive_drive}: cleanup error: {e}")

            # 4. Qdrive data → Backup drive
            logger.info(f"Qdrive to Backup copy conditions:")
            logger.info(f"   copy_plan['qdrive_to_backup']: {self.copy_plan['qdrive_to_backup']}")
            logger.info(f"   qdrive_drives: {self.qdrive_drives}")
            logger.info(f"   backup_drive: {self.backup_drive}")
            logger.info(f"   qdrive_handler: {qdrive_handler}")
            logger.info(f"   qdrive_number_mapping: {getattr(self, 'qdrive_number_mapping', 'NOT_SET')}")
            
            if self.copy_plan['qdrive_to_backup'] and self.qdrive_drives and self.backup_drive and qdrive_handler:
                print(f"SUCCESS: Starting Qdrive to Backup drive copy task...")
                for qdrive_drive in self.qdrive_drives:
                    drive_number = self.qdrive_number_mapping.get(qdrive_drive, 'Unknown')
                    task_id = f"Qdrive {drive_number} → Backup"
                    
                    # Add task to progress tracker (only for 201, 203, 230, 231)
                    if drive_number in ['201', '203', '230', '231']:
                        progress_tracker.add_task(task_id, qdrive_drive, self.backup_drive)
                    
                    def copy_qdrive_to_backup(drive=qdrive_drive, number=drive_number, task_id=task_id):
                        try:
                            success = self.detector.copy_qdrive_data_to_backup(drive, self.backup_drive, qdrive_handler, number)
                            copy_results[f"qdrive_{number}_to_backup"] = success
                            if success:
                                pass
                            else:
                                print(f"ERROR: Qdrive {number} ({drive}) → {self.backup_drive} copy failed")
                        except Exception as e:
                            copy_results[f"qdrive_{number}_to_backup"] = False
                            print(f"ERROR: Qdrive {number} ({drive}) → {self.backup_drive} copy error: {e}")
                    
                    thread = threading.Thread(target=copy_qdrive_to_backup)
                    copy_threads.append(thread)
                    thread.start()
                    logger.info(f"Started Qdrive {drive_number} ({qdrive_drive}) to Backup copy task")
            
            # Wait for all copy tasks to complete
            print(f"\nWaiting for all copy tasks to complete...")
            logger.info(f"Total started {len(copy_threads)} copy tasks")
            
            # The detailed progress tracker will handle display automatically
            # Wait for all threads to complete with timeout
            for thread in copy_threads:
                thread.join(timeout=300)  # Wait up to 5 minutes for each thread (increased from 30s)
                if thread.is_alive():
                    logger.warning(f"Thread {thread.name} did not complete within timeout (5 minutes)")
            
            # Ensure all tasks are marked as completed before stopping progress tracker
            try:
                from utils.detailed_progress import get_progress_tracker
            except ImportError:
                from data_copy_modules.utils.detailed_progress import get_progress_tracker
            progress_tracker = get_progress_tracker()
            
            # Check for any remaining running tasks and wait for them to complete naturally
            with progress_tracker.lock:
                running_tasks = [task_id for task_id, task in progress_tracker.tasks.items() 
                               if task['status'] == 'running']
            
            if running_tasks:
                print(f"[WARNING] Warning: {len(running_tasks)} tasks still running: {running_tasks}")
                print("Waiting additional time for tasks to complete naturally...")
                # Wait a bit more for tasks to complete naturally
                time.sleep(10)  # 增加等待时间
                
                # Check again and only mark as completed if they're truly done
                with progress_tracker.lock:
                    for task_id in running_tasks:
                        if task_id in progress_tracker.tasks and progress_tracker.tasks[task_id]['status'] == 'running':
                            # 不要强制标记为完成，让任务自然完成
                            # 这样可以保持进度条的准确性
                            print(f"[WARNING] Task {task_id} still running, waiting for natural completion...")
                            # 移除强制完成逻辑，让进度条保持实际状态
            
            # Wait a moment for the progress display to update
            time.sleep(2)
            
            # Stop the progress tracker
            try:
                from utils.detailed_progress import stop_progress_tracker
            except ImportError:
                from data_copy_modules.utils.detailed_progress import stop_progress_tracker
            stop_progress_tracker()
            
            # Post-copy integrity verification
            overall_verified = True
            try:
                from utils.file_utils import get_directory_stats
            except ImportError:
                from data_copy_modules.utils.file_utils import get_directory_stats

            def _safe_stats(path: str):
                try:
                    if path and os.path.exists(path):
                        return get_directory_stats(path)
                except Exception:
                    pass
                return {'file_count': 0, 'total_size': 0}

            def _sum_qdrive_sources(qdrives):
                total_files = 0
                total_size = 0
                drive_details = []
                for d in (qdrives or []):
                    sp = os.path.join(d, 'data')
                    st = _safe_stats(sp)
                    total_files += st['file_count']
                    total_size += st['total_size']
                    
                    # Get drive number from mapping or extract from drive path
                    drive_number = self.qdrive_number_mapping.get(d, None)
                    if not drive_number:
                        # fallback extract 3 digits
                        import re
                        m = re.search(r'(201|203|230|231)', d)
                        drive_number = m.group(1) if m else 'UNKNOWN'
                    
                    drive_details.append(f"{d}data (Qdrive {drive_number}): {st['file_count']} files, {st['total_size']} bytes")
                return {'file_count': total_files, 'total_size': total_size, 'details': drive_details}

            def _find_backup_qdrive_data_path(backup_drive: str, drive_number: str):
                try:
                    roots = [p for p in os.listdir(backup_drive)
                             if os.path.isdir(os.path.join(backup_drive, p)) and not p.startswith('.')]
                except Exception:
                    return None
                # Prefer latest root by name ordering
                for root in sorted(roots, reverse=True):
                    root_path = os.path.join(backup_drive, root)
                    try:
                        for sub in os.listdir(root_path):
                            if drive_number in sub:
                                dp = os.path.join(root_path, sub, 'data')
                                if os.path.isdir(dp):
                                    return dp
                    except Exception:
                        continue
                return None

            verification_messages = []

            # 1) Sum of 4 Qdrives data vs Transfer /data
            if self.transfer_drive and self.qdrive_drives:
                q_sum = _sum_qdrive_sources(self.qdrive_drives)
                t_data = _safe_stats(os.path.join(self.transfer_drive, 'data'))
                tolerance = self.config_manager.get_verification_tolerance()
                ok1 = (q_sum['file_count'] == t_data['file_count'] and
                       abs(q_sum['total_size'] - t_data['total_size']) < tolerance)
                overall_verified = overall_verified and ok1
                
                # Add detailed calculation process
                calc_msg = f"Qdrive→Transfer /data calculation:\n"
                for detail in q_sum['details']:
                    calc_msg += f"  + {detail}\n"
                calc_msg += f"  = Total: {q_sum['file_count']} files, {q_sum['total_size']} bytes"
                verification_messages.append(calc_msg)
                verification_messages.append(f"Qdrive→Transfer /data match: {'OK' if ok1 else 'MISMATCH'} | src files {q_sum['file_count']}, bytes {q_sum['total_size']} vs dst files {t_data['file_count']}, bytes {t_data['total_size']}")

            # 2) Vector logs sum vs Transfer /logs
            if self.transfer_drive and self.vector_drive:
                v_src = _safe_stats(os.path.join(self.vector_drive, 'logs'))
                t_logs = _safe_stats(os.path.join(self.transfer_drive, 'logs'))
                ok2 = (v_src['file_count'] == t_logs['file_count'] and
                       abs(v_src['total_size'] - t_logs['total_size']) < tolerance)
                overall_verified = overall_verified and ok2
                verification_messages.append(f"Vector→Transfer /logs match: {'OK' if ok2 else 'MISMATCH'} | src files {v_src['file_count']}, bytes {v_src['total_size']} vs dst files {t_logs['file_count']}, bytes {t_logs['total_size']}")

            # 3) Each Qdrive data vs its Backup mapped folder
            if self.backup_drive and self.qdrive_drives:
                for d in self.qdrive_drives:
                    # determine drive_number
                    drive_number = self.qdrive_number_mapping.get(d, None)
                    if not drive_number:
                        # fallback extract 3 digits
                        import re
                        m = re.search(r'(201|203|230|231)', d)
                        drive_number = m.group(1) if m else 'UNKNOWN'
                    src_stats = _safe_stats(os.path.join(d, 'data'))
                    dst_path = _find_backup_qdrive_data_path(self.backup_drive, drive_number)
                    dst_stats = _safe_stats(dst_path) if dst_path else {'file_count': 0, 'total_size': 0}
                    ok3 = (src_stats['file_count'] == dst_stats['file_count'] and
                           abs(src_stats['total_size'] - dst_stats['total_size']) < tolerance)
                    overall_verified = overall_verified and ok3
                    verification_messages.append(f"Qdrive {drive_number}→Backup match: {'OK' if ok3 else 'MISMATCH'} | src files {src_stats['file_count']}, bytes {src_stats['total_size']} vs dst files {dst_stats['file_count']}, bytes {dst_stats['total_size']}")

            # 4) Vector logs sum vs Backup logs target
            if self.backup_drive and self.vector_drive:
                v_src2 = _safe_stats(os.path.join(self.vector_drive, 'logs'))
                # Determine backup logs target heuristic
                backup_logs_path = None
                # try to detect a root containing 'logs' folder
                try:
                    roots = [p for p in os.listdir(self.backup_drive)
                             if os.path.isdir(os.path.join(self.backup_drive, p)) and not p.startswith('.')]
                    for root in sorted(roots, reverse=True):
                        cand = os.path.join(self.backup_drive, root, 'logs')
                        if os.path.isdir(cand):
                            backup_logs_path = cand
                            break
                except Exception:
                    pass
                if not backup_logs_path:
                    # fallback: backup root or backup\logs if exists
                    fallback = os.path.join(self.backup_drive, 'logs')
                    backup_logs_path = fallback if os.path.isdir(fallback) else self.backup_drive
                v_dst2 = _safe_stats(backup_logs_path)
                ok4 = (v_src2['file_count'] == v_dst2['file_count'] and
                       abs(v_src2['total_size'] - v_dst2['total_size']) < tolerance)
                overall_verified = overall_verified and ok4
                verification_messages.append(f"Vector→Backup logs match: {'OK' if ok4 else 'MISMATCH'} | src files {v_src2['file_count']}, bytes {v_src2['total_size']} vs dst files {v_dst2['file_count']}, bytes {v_dst2['total_size']}")

            print("\n" + "="*80)
            print("Post-copy integrity verification results:")
            for msg in verification_messages:
                print(" - " + msg)
            print("="*80 + "\n")
            
            # Log verification results to file
            try:
                from logging_utils.copy_logger import log_copy_operation
                log_copy_operation("="*80)
                log_copy_operation("Post-copy integrity verification results:")
                for msg in verification_messages:
                    log_copy_operation(f" - {msg}")
                log_copy_operation(f"Overall verification status: {'PASSED' if overall_verified else 'FAILED'}")
                log_copy_operation("="*80)
            except ImportError:
                try:
                    from data_copy_modules.logging_utils.copy_logger import log_copy_operation
                    log_copy_operation("="*80)
                    log_copy_operation("Post-copy integrity verification results:")
                    for msg in verification_messages:
                        log_copy_operation(f" - {msg}")
                    log_copy_operation(f"Overall verification status: {'PASSED' if overall_verified else 'FAILED'}")
                    log_copy_operation("="*80)
                except Exception as e:
                    print(f"Warning: Could not log verification results: {e}")
            except Exception as e:
                print(f"Warning: Could not log verification results: {e}")

            # Gate overall success on verification
            if not overall_verified:
                # force overall failure
                copy_results["__verification__"] = False
            else:
                copy_results["__verification__"] = True

            # Export Vector folder structure (third-level dirs under logs) after copy
            if self.vector_drive and (copy_results.get("vector_to_transfer", False) or copy_results.get("vector_to_backup", False)):
                try:
                    success = self.detector._export_vector_third_level_dirs(self.vector_drive)
                    if success:
                        print("SUCCESS: Exported Vector folder structure to folderstructure.txt")
                    else:
                        print("[WARNING] Exporting Vector folder structure was skipped or failed")
                except Exception as e:
                    print(f"ERROR: Error exporting Vector folder structure: {e}")

            # Rename Qdrive 'data' folder(s) to archive format after all copy tasks complete
            if self.qdrive_drives:
                print("\nPROCESSING: Renaming Qdrive data folder(s) to archive format...")
                for qdrive_drive in self.qdrive_drives:
                    try:
                        # Pass vector drive so Qdrive rename uses earliest Vector date-time folder
                        result = self.detector._rename_qdrive_data_to_archive(qdrive_drive, self.vector_drive)
                        if result:
                            print(f"SUCCESS: Qdrive data folder on {qdrive_drive} renamed successfully, using date: {result}")
                        else:
                            print(f"[WARNING] Qdrive data folder rename skipped or failed on {qdrive_drive}")
                    except Exception as e:
                        print(f"ERROR: Error renaming Qdrive data folder on {qdrive_drive}: {e}")
            
            # Count copy results
            total_tasks = len(copy_results)
            successful_tasks = sum(1 for success in copy_results.values() if success)
            failed_tasks = total_tasks - successful_tasks
            
            if failed_tasks == 0:
                return True
            else:
                print(f"\n[WARNING] {failed_tasks} tasks failed, detailed failure information below:")
                print("="*60)
                
                # Display detailed status of each task
                for task_name, success in copy_results.items():
                    status_icon = "SUCCESS:" if success else "ERROR:"
                    status_text = "Success" if success else "Failed"
                    print(f"{status_icon} {task_name}: {status_text}")
                
                print("="*60)
                print("💡 Suggestions:")
                print("   1. Check source and target drives for failed tasks")
                print("   2. Confirm sufficient disk space")
                print("   3. Check file permissions and if files are in use")
                print("   4. You can re-run failed tasks individually")
                return False
            
        except Exception as e:
            print(f"ERROR: Error executing copy plan: {e}")
            logger.error(f"Error executing copy plan: {e}", exc_info=True)
            return False
    
    def print_summary(self):
        """Print operation summary"""
        print("\n" + "="*60)
        print("Operation Summary:")
        print("="*60)
        
        print(f"Operating System: {self.detector.os_type}")
        print("Qdrive Drives:")
        logger.info(f"qdrive_number_mapping exists: {hasattr(self, 'qdrive_number_mapping')}")
        if hasattr(self, 'qdrive_number_mapping'):
            logger.info(f"qdrive_number_mapping content: {self.qdrive_number_mapping}")
        if hasattr(self, 'qdrive_number_mapping') and self.qdrive_number_mapping:
            for drive, number in self.qdrive_number_mapping.items():
                print(f"  {number}: {drive}")
        else:
            print(f"  {self.qdrive_drives}")
        print(f"Vector Drive: {self.vector_drive}")
        print(f"Transfer Drive: {self.transfer_drive}")
        print(f"Backup Drive: {self.backup_drive}")
        print(f"Copy Plan: {self.copy_plan}")
        
        print("\n" + "="*60)
    
    def run(self):
        """Run interactive data copy tool"""
        print("Interactive Data Copy Tool")
        print("="*60)
        print("This tool will guide you through the following steps:")
        print("1. Identify all external drives")
        print("2. Handle BitLocker unlock (if needed)")
        print("3. Select Qdrive data drives (201, 203, 230, 231)")
        print("4. Select Vector data drive")
        print("5. Select Transfer target drive")
        print("6. Select Backup target drive")
        print("7. Check Vector data dates")
        print("8. Create copy plan")
        print("9. Execute data copy")
        print("="*60)
        
        try:
            # 1. Show all external drives
            external_drives = self.show_all_drives()
            if not external_drives:
                print("ERROR: No available external drives, program exiting")
                return
            
            # 2. Handle BitLocker unlock (before drive selection)
            if not self.handle_bitlocker_unlock(external_drives):
                print("ERROR: BitLocker unlock failed, program exiting")
                return
            
            # 3. Automatically identify all drives
            print("\n3. Automatically identifying drives...")
            qdrive_drives, vector_drives, transfer_drives, backup_drives = self.detector.identify_data_drives(require_confirmation=True)
            
            # Check if user chose to quit (all lists are empty)
            if not qdrive_drives and not vector_drives and not transfer_drives and not backup_drives:
                print("[EXIT] User chose to exit. Program terminated.")
                return
            
            # Store the identified drives
            self.qdrive_drives = qdrive_drives
            self.vector_drive = vector_drives[0] if vector_drives else None
            self.transfer_drive = transfer_drives[0] if transfer_drives else None
            self.backup_drive = backup_drives[0] if backup_drives else None
            
            # Validate vehicle model if Vector drive is detected
            if self.vector_drive:
                print("\n" + "="*60)
                print("Vehicle Model Validation:")
                print("="*60)
                
                detected_model = self._detect_vehicle_model_from_vector(self.vector_drive)
                validation_message = self.config_manager.get_vehicle_validation_message(detected_model)
                print(validation_message)
                
                if not self.config_manager.validate_vehicle_model(detected_model):
                    border = "*" * 70
                    print("\n" + border)
                    print("ERROR: VEHICLE MODEL VALIDATION FAILED!")
                    print("ERROR: Copy operation will be aborted.")
                    print("ERROR: Configuration validation failed")
                    print("ERROR: Expected vehicle model:", self.config_manager.get_expected_vehicle_model())
                    print("ERROR: Detected vehicle model:", detected_model)
                    print(border)
                    return
            
            # Store Qdrive number mapping from detector
            logger.info(f"detector.qdrive_number_mapping exists: {hasattr(self.detector, 'qdrive_number_mapping')}")
            if hasattr(self.detector, 'qdrive_number_mapping'):
                logger.info(f"detector.qdrive_number_mapping content: {self.detector.qdrive_number_mapping}")
                self.qdrive_number_mapping = self.detector.qdrive_number_mapping
            else:
                logger.warning("detector.qdrive_number_mapping does not exist")
            
            # If no transfer drive was automatically identified, allow manual selection
            if not self.transfer_drive:
                print("\n[WARNING] No Transfer drive was automatically identified.")
                print("You can manually select a Transfer drive if needed.")
                choice = input("Do you want to manually select a Transfer drive? (y/n): ").lower().strip()
                if choice == 'y':
                    self.transfer_drive = self.select_transfer_drive(external_drives)
                    if self.transfer_drive:
                        print(f"SUCCESS: Transfer drive manually selected: {self.transfer_drive}")
                    else:
                        print("ERROR: No Transfer drive selected")
            
            # If no backup drive was automatically identified, allow manual selection
            if not self.backup_drive:
                print("\n[WARNING] No Backup drive was automatically identified.")
                print("You can manually select a Backup drive if needed.")
                choice = input("Do you want to manually select a Backup drive? (y/n): ").lower().strip()
                if choice == 'y':
                    self.backup_drive = self.select_backup_drive(external_drives)
                    if self.backup_drive:
                        print(f"SUCCESS: Backup drive manually selected: {self.backup_drive}")
                    else:
                        print("ERROR: No Backup drive selected")
            
            # Display final drive binding status after all selections
            print("\n" + "="*60)
            print("CHECKING: Final Drive Binding Status:")
            print("="*60)
            print(f"Qdrive drives: {self.qdrive_drives}")
            print(f"Vector drive: {self.vector_drive}")
            print(f"Transfer drive: {self.transfer_drive}")
            print(f"Backup drive: {self.backup_drive}")
            print("="*60)
            
            # 7. Check duplicate status against previous logs (before creating copy plan)
            if self.vector_drive:
                print("\n" + "="*60)
                print("Checking Vector duplicate status against previous logs...")
                print("="*60)
                try:
                    has_dup, dups = self.detector.check_vector_duplicate_third_level(self.vector_drive)
                    if has_dup:
                        print("ERROR: Duplicate Vector date-time folders found compared to previous logs:")
                        for name in dups:
                            print(f"   - {name}")
                        print("Note: The task will be aborted right after the confirmation step to avoid duplicate copying.")
                    else:
                        print("SUCCESS: No duplicate Vector date-time folders found compared to previous logs.")
                except Exception as e:
                    print(f"[WARNING] Unable to perform duplicate check: {e}")
                    
                    confirm = input("\nDo you still want to continue with copy plan? (y/n): ").lower().strip()
                    if confirm != 'y':
                        print("Copy plan cancelled")
                        return
            
            # 8. Create copy plan
            self.create_copy_plan()
            
            # 9. Confirm execution
            print("\n" + "="*60)
            print("All selections completed, ready to execute copy plan")
            self.print_summary()
            
            confirm = input("\nStart executing copy plan? (y/n): ").lower().strip()
            if confirm == 'y':
                # 10. Execute copy plan
                success = self.execute_copy_plan()
                if success:
                    print("\n🎉 Data copy task completed!")
                else:
                    print("\nERROR: Data copy task failed")
            else:
                print("Operation cancelled")
            
        except KeyboardInterrupt:
            print("\n\nUser interrupted operation")
        except Exception as e:
            print(f"\nProgram execution error: {e}")
            logger.error(f"Program execution error: {e}", exc_info=True)
        finally:
            print("\nProgram execution completed")
            # Prevent auto-close of console window in packaged exe
            try:
                input("\nPress Enter to exit...")
            except (EOFError, KeyboardInterrupt):
                pass

def main():
    """Main function"""
    # Create and run interactive tool
    tool = InteractiveDataCopyTool()
    tool.run()

if __name__ == "__main__":
    main()
