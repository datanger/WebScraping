#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive Confirmation Interface Module
"""

import os
import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class ConfirmationInterface:
    """Interactive Confirmation Interface Class"""
    
    def __init__(self):
        """Initialize confirmation interface"""
        self.line_width = 80
        self.section_separator = "=" * self.line_width
        self.subsection_separator = "-" * 50
    
    def display_identification_results(self, 
                                     qdrive_drives: List[str], 
                                     vector_drives: List[str], 
                                     transfer_drives: List[str], 
                                     backup_drives: List[str],
                                     analyzer,
                                     qdrive_number_mapping: Dict[str, str] = None) -> str:
        """
        Display identification results and wait for user confirmation
        
        Args:
            qdrive_drives: List of Qdrive drives
            vector_drives: List of Vector drives
            transfer_drives: List of Transfer drives
            backup_drives: List of Backup drives
            analyzer: Directory structure analyzer instance
            
        Returns:
            str: User choice (Y/N/M/Q)
        """
        print("\n" + self.section_separator)
        print("CHECKING: AUTOMATED DRIVE IDENTIFICATION RESULTS")
        print(self.section_separator)
        
        # Display Qdrive identification results
        if qdrive_drives:
            self._display_qdrive_results(qdrive_drives, analyzer, qdrive_number_mapping)
        
        # Display Vector identification results
        if vector_drives:
            self._display_vector_results(vector_drives, analyzer)
        
        # Display Transfer identification results
        if transfer_drives:
            self._display_transfer_results(transfer_drives, analyzer)
        
        # Display Backup identification results
        if backup_drives:
            self._display_backup_results(backup_drives, analyzer)
        
        # Display summary information
        self._display_summary(qdrive_drives, vector_drives, transfer_drives, backup_drives, qdrive_number_mapping)
        
        # User confirmation options
        return self._get_user_confirmation()
    
    def _display_qdrive_results(self, qdrive_drives: List[str], analyzer, qdrive_number_mapping: Dict[str, str] = None):
        """Display Qdrive identification results with folder structure"""
        print(f"\n[QDRIVE] QDRIVE DATA DRIVES ({len(qdrive_drives)} drives):")
        print(self.subsection_separator)
        
        for i, drive in enumerate(qdrive_drives, 1):
            # Get the specific Qdrive number for this drive
            qdrive_number = "Unknown"
            if qdrive_number_mapping and drive in qdrive_number_mapping:
                qdrive_number = qdrive_number_mapping[drive]
            
            print(f"\n  -> Qdrive {qdrive_number}: {drive}")
            
            # Show simple folder structure
            self._show_simple_folder_structure(drive)
            
            # Show detection reason
            self._show_detection_reason(drive, "Qdrive")
    
    def _display_vector_results(self, vector_drives: List[str], analyzer):
        """Display Vector identification results with folder structure"""
        print(f"\n[VECTOR] VECTOR DATA DRIVES ({len(vector_drives)} drives):")
        print(self.subsection_separator)
        
        for i, drive in enumerate(vector_drives, 1):
            print(f"\n  -> Vector {i}: {drive}")
            
            # Show simple folder structure
            self._show_simple_folder_structure(drive)
            
            # Show detection reason
            self._show_detection_reason(drive, "Vector")
    
    def _display_transfer_results(self, transfer_drives: List[str], analyzer):
        """Display Transfer identification results with folder structure"""
        print(f"\nPROCESSING: TRANSFER DRIVES ({len(transfer_drives)} drives):")
        print(self.subsection_separator)
        
        for i, drive in enumerate(transfer_drives, 1):
            print(f"\n  -> Transfer {i}: {drive}")
            
            # Show simple folder structure
            self._show_simple_folder_structure(drive)
            
            # Show detection reason
            self._show_detection_reason(drive, "Transfer")
    
    def _display_backup_results(self, backup_drives: List[str], analyzer):
        """Display Backup identification results with folder structure"""
        print(f"\n[BACKUP] BACKUP DRIVES ({len(backup_drives)} drives):")
        print(self.subsection_separator)
        
        for i, drive in enumerate(backup_drives, 1):
            print(f"\n  -> Backup {i}: {drive}")
            
            # Show simple folder structure
            self._show_simple_folder_structure(drive)
            
            # Show detection reason
            self._show_detection_reason(drive, "Backup")
    
    def _display_summary(self, qdrive_drives: List[str], vector_drives: List[str], 
                        transfer_drives: List[str], backup_drives: List[str], 
                        qdrive_number_mapping: Dict[str, str] = None):
        """Display summary information"""
        print(f"\n[SUMMARY] IDENTIFICATION SUMMARY:")
        print(self.subsection_separator)
        
        total_drives = len(qdrive_drives) + len(vector_drives) + len(transfer_drives) + len(backup_drives)
        
        # Display Qdrive detailed information
        if qdrive_drives:
            print(f"   [QDRIVE] Qdrive Data Drives: {len(qdrive_drives)}")
            if qdrive_number_mapping:
                # Group by drive number for display
                qdrive_by_number = {}
                for drive, number in qdrive_number_mapping.items():
                    if number not in qdrive_by_number:
                        qdrive_by_number[number] = []
                    qdrive_by_number[number].append(drive)
                
                for number in sorted(qdrive_by_number.keys()):
                    drives = qdrive_by_number[number]
                    print(f"      └── Qdrive {number}: {', '.join(drives)}")
            else:
                print(f"      └── Drives: {', '.join(qdrive_drives)}")
        else:
            print(f"   [QDRIVE] Qdrive Data Drives: 0")
        
        print(f"   [VECTOR] Vector Data Drives: {len(vector_drives)}")
        if vector_drives:
            print(f"      └── Drives: {', '.join(vector_drives)}")
        
        print(f"   PROCESSING: Transfer Drives: {len(transfer_drives)}")
        if transfer_drives:
            print(f"      └── Drives: {', '.join(transfer_drives)}")
        
        print(f"   [BACKUP] Backup Drives: {len(backup_drives)}")
        if backup_drives:
            print(f"      └── Drives: {', '.join(backup_drives)}")
        
        print(f"   [TOTAL] Total Drives: {total_drives}")
        
        # Display identification time
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"   [TIME] Identification Time: {current_time}")
    
    def _get_user_confirmation(self) -> str:
        """Get user confirmation for drive identification results"""
        print(f"\n{self.section_separator}")
        print("[CONFIRM] DRIVE IDENTIFICATION CONFIRMATION")
        print(self.section_separator)
        print("Please review the folder structures and detection reasons above.")
        print("Make sure the drives are correctly identified before proceeding.")
        print("\nOptions:")
        print("  [Y] Yes, the identification is correct - proceed with data copy")
        print("  [N] No, re-run the automatic identification")
        print("  [M] Manual adjustment - modify the drive assignments")
        print("  [Q] Quit - exit the program")
        
        while True:
            try:
                choice = input("\nYour choice (Y/N/M/Q): ").strip().upper()
                if choice in ['Y', 'N', 'M', 'Q']:
                    return choice
                else:
                    print("ERROR: Invalid choice. Please enter Y, N, M, or Q.")
            except KeyboardInterrupt:
                print("\n\n[EXIT] Operation cancelled by user.")
                return 'Q'
            except Exception as e:
                print(f"ERROR: Input error: {e}")
                print("Please try again.")
    
    def handle_user_confirmation(self, choice: str, detector, current_qdrive_drives: List[str] = None,
                                current_vector_drives: List[str] = None,
                                current_transfer_drives: List[str] = None,
                                current_backup_drives: List[str] = None) -> Tuple[bool, List[str], List[str], List[str], List[str]]:
        """
        Handle user confirmation choice
        
        Args:
            choice: User choice
            detector: Drive detector instance
            current_qdrive_drives: Currently selected Qdrive drives
            current_vector_drives: Currently selected Vector drives
            current_transfer_drives: Currently selected Transfer drives
            current_backup_drives: Currently selected Backup drives
            
        Returns:
            Tuple[bool, List[str], List[str], List[str], List[str]]: 
            (should_continue, qdrive_drives, vector_drives, transfer_drives, backup_drives)
        """
        if choice == 'Y':
            print("SUCCESS: Proceeding with data copy...")
            return True, None, None, None, None
        elif choice == 'N':
            print("PROCESSING: Re-identifying drives...")
            # Re-identify drives without confirmation to avoid infinite recursion
            qdrive_drives, vector_drives, transfer_drives, backup_drives = detector.identify_data_drives(require_confirmation=False)
            return False, qdrive_drives, vector_drives, transfer_drives, backup_drives
        elif choice == 'M':
            print("🔧 Manual adjustment mode...")
            return self._manual_drive_adjustment(detector, current_qdrive_drives, 
                                               current_vector_drives, current_transfer_drives, 
                                               current_backup_drives)
        elif choice == 'Q':
            print("[EXIT] Exiting...")
            return False, [], [], [], []
    
    def _manual_drive_adjustment(self, detector, current_qdrive_drives: List[str] = None, 
                                current_vector_drives: List[str] = None,
                                current_transfer_drives: List[str] = None,
                                current_backup_drives: List[str] = None) -> Tuple[bool, List[str], List[str], List[str], List[str]]:
        """
        Manual drive adjustment - allows user to manually assign drive types
        
        Args:
            detector: Drive detector instance
            current_qdrive_drives: Currently selected Qdrive drives
            current_vector_drives: Currently selected Vector drives
            current_transfer_drives: Currently selected Transfer drives
            current_backup_drives: Currently selected Backup drives
            
        Returns:
            Tuple[bool, List[str], List[str], List[str], List[str]]: 
            (should_continue, qdrive_drives, vector_drives, transfer_drives, backup_drives)
        """
        print("\n🔧 MANUAL DRIVE ADJUSTMENT")
        print(self.subsection_separator)
        print("You can now manually assign drive types to each detected drive.")
        print("This allows you to override the automatic detection results.")
        
        # Get all available drives
        all_drives = detector.exclude_system_drives()
        if not all_drives:
            print("ERROR: No available drives found for manual adjustment")
            return False, [], [], [], []
        
        # Get currently selected drives
        current_qdrive_drives = current_qdrive_drives or []
        current_vector_drives = current_vector_drives or []
        current_transfer_drives = current_transfer_drives or []
        current_backup_drives = current_backup_drives or []
        
        # Combine all currently selected drives
        all_selected_drives = set(current_qdrive_drives + current_vector_drives + 
                                 current_transfer_drives + current_backup_drives)
        
        # Show all drives for manual adjustment (including already assigned ones)
        print(f"\nAll available drives for manual adjustment: {all_drives}")
        if all_selected_drives:
            print(f"Currently assigned drives: {sorted(all_selected_drives)}")
        
        # Ask user if they want to reassign all drives or just unassigned ones
        print("\nManual adjustment options:")
        print("  [1] Reassign all drives (including currently assigned)")
        print("  [2] Only assign unassigned drives")
        print("  [3] Cancel manual adjustment")
        
        while True:
            try:
                mode_choice = input("Select adjustment mode (1-3): ").strip()
                if mode_choice in ['1', '2', '3']:
                    break
                else:
                    print("ERROR: Invalid choice. Please enter 1-3.")
            except KeyboardInterrupt:
                print("\n[EXIT] Manual adjustment cancelled")
                return False, [], [], [], []
        
        if mode_choice == '3':
            print("Manual adjustment cancelled")
            return False, [], [], [], []
        
        if mode_choice == '1':
            # Reassign all drives - clear current assignments
            available_drives = all_drives
            qdrive_drives = []
            vector_drives = []
            transfer_drives = []
            backup_drives = []
            print("PROCESSING: All drives will be reassigned")
        else:
            # Only assign unassigned drives
            available_drives = [drive for drive in all_drives if drive not in all_selected_drives]
            if not available_drives:
                print("ERROR: No unassigned drives available for manual adjustment")
                print(f"All drives have been assigned: {sorted(all_selected_drives)}")
                return False, [], [], [], []
            print(f"📝 Only unassigned drives will be assigned: {available_drives}")
            # Keep current assignments
            qdrive_drives = current_qdrive_drives.copy()
            vector_drives = current_vector_drives.copy()
            transfer_drives = current_transfer_drives.copy()
            backup_drives = current_backup_drives.copy()
        
        # Create Qdrive number mapping for manual assignments
        qdrive_number_mapping = {}
        
        # Track which types have been selected to avoid duplicates
        selected_types = set()
        
        # Define all available types with their descriptions
        all_types = {
            '1': ('Qdrive 201', 'camera_fc*.mp4 files'),
            '2': ('Qdrive 203', 'camera_rc*.mp4 files'),
            '3': ('Qdrive 230', 'data_lidar_top folder'),
            '4': ('Qdrive 231', 'data_lidar_front folder'),
            '5': ('Vector', 'Logs/logs folder'),
            '6': ('Transfer', 'Echo* but not backup'),
            '7': ('Backup', 'Echo*backup or default'),
            '8': ('Skip', 'Skip this drive')
        }
        
        # Manual assignment for each drive
        for drive in available_drives:
            print(f"\nINFO: Drive: {drive}")
            self._show_simple_folder_structure(drive)
            
            # Show only available types (not yet selected)
            available_choices = []
            print("\nDrive type options:")
            option_num = 1
            for type_key, (type_name, description) in all_types.items():
                if type_key not in selected_types:
                    print(f"  [{option_num}] {type_name} ({description})")
                    available_choices.append(type_key)
                    option_num += 1
            
            # Always show skip option
            if '8' not in available_choices:
                print(f"  [{option_num}] Skip this drive")
                available_choices.append('8')
                option_num += 1
            
            # Get valid input range
            max_choice = len(available_choices)
            
            while True:
                try:
                    choice_input = input(f"Select type for {drive} (1-{max_choice}): ").strip()
                    if choice_input.isdigit() and 1 <= int(choice_input) <= max_choice:
                        # Map the input choice to the actual type key
                        actual_choice = available_choices[int(choice_input) - 1]
                        break
                    else:
                        print(f"ERROR: Invalid choice. Please enter 1-{max_choice}.")
                except KeyboardInterrupt:
                    print("\n[EXIT] Manual adjustment cancelled")
                    return False, [], [], [], []
            
            # Assign drive to appropriate list
            if actual_choice == '1':
                qdrive_drives.append(drive)
                qdrive_number_mapping[drive] = '201'
                selected_types.add('1')
                print(f"SUCCESS: {drive} assigned as Qdrive 201")
            elif actual_choice == '2':
                qdrive_drives.append(drive)
                qdrive_number_mapping[drive] = '203'
                selected_types.add('2')
                print(f"SUCCESS: {drive} assigned as Qdrive 203")
            elif actual_choice == '3':
                qdrive_drives.append(drive)
                qdrive_number_mapping[drive] = '230'
                selected_types.add('3')
                print(f"SUCCESS: {drive} assigned as Qdrive 230")
            elif actual_choice == '4':
                qdrive_drives.append(drive)
                qdrive_number_mapping[drive] = '231'
                selected_types.add('4')
                print(f"SUCCESS: {drive} assigned as Qdrive 231")
            elif actual_choice == '5':
                vector_drives.append(drive)
                selected_types.add('5')
                print(f"SUCCESS: {drive} assigned as Vector drive")
            elif actual_choice == '6':
                transfer_drives.append(drive)
                selected_types.add('6')
                print(f"SUCCESS: {drive} assigned as Transfer drive")
            elif actual_choice == '7':
                backup_drives.append(drive)
                selected_types.add('7')
                print(f"SUCCESS: {drive} assigned as Backup drive")
            elif actual_choice == '8':
                print(f"[SKIP] {drive} skipped")
                # Don't add '8' to selected_types as skip can be used multiple times
        
        # Display final assignment
        print(f"\n[SUMMARY] MANUAL ASSIGNMENT SUMMARY:")
        print(f"[QDRIVE] Qdrive drives: {qdrive_drives}")
        print(f"[VECTOR] Vector drives: {vector_drives}")
        print(f"[TRANSFER] Transfer drives: {transfer_drives}")
        print(f"[BACKUP] Backup drives: {backup_drives}")
        logger.info(f"qdrive_number_mapping: {qdrive_number_mapping}")
        
        # Confirm the assignment
        while True:
            try:
                confirm = input("\nConfirm this assignment? (y/n): ").lower().strip()
                if confirm in ['y', 'n']:
                    break
                else:
                    print("ERROR: Please enter 'y' or 'n'.")
            except KeyboardInterrupt:
                print("\n[EXIT] Manual adjustment cancelled")
                return False, [], [], [], []
        
        if confirm == 'y':
            print("SUCCESS: Manual assignment confirmed. Proceeding with data copy...")
            # Save Qdrive number mapping to detector
            detector.qdrive_number_mapping = qdrive_number_mapping
            logger.info(f"Saved qdrive_number_mapping to detector: {qdrive_number_mapping}")
            return True, qdrive_drives, vector_drives, transfer_drives, backup_drives
        else:
            print("PROCESSING: Manual assignment cancelled. Returning to main menu...")
            return False, qdrive_drives, vector_drives, transfer_drives, backup_drives
    
    def display_confirmation_result(self, choice: str):
        """Display confirmation result"""
        if choice == 'Y':
            print("SUCCESS: User confirmed identification results. Proceeding with data copy...")
        elif choice == 'N':
            print("PROCESSING: User requested re-identification. Re-analyzing drives...")
        elif choice == 'M':
            print("🔧 User requested manual adjustment. Entering adjustment mode...")
        elif choice == 'Q':
            print("[EXIT] User chose to quit. Exiting program...")
    
    def display_error_message(self, message: str):
        """Display error message"""
        print(f"\nERROR: ERROR: {message}")
        print(self.subsection_separator)
    
    def display_success_message(self, message: str):
        """Display success message"""
        print(f"\nSUCCESS: SUCCESS: {message}")
        print(self.subsection_separator)
    
    def display_warning_message(self, message: str):
        """Display warning message"""
        print(f"\n[WARNING] WARNING: {message}")
        print(self.subsection_separator)
    
    def _show_simple_folder_structure(self, drive_path: str):
        """Show detailed folder structure for a drive with file types and examples"""
        try:
            if not os.access(drive_path, os.R_OK):
                print("   ERROR: Cannot access drive")
                return
            
            # Get root directory contents
            entries = os.listdir(drive_path)
            folders = [entry for entry in entries if os.path.isdir(os.path.join(drive_path, entry))]
            files = [entry for entry in entries if os.path.isfile(os.path.join(drive_path, entry))]
            
            # Filter out system folders that cause access denied errors
            system_folders = {'$RECYCLE.BIN', 'System Volume Information', '$Recycle.Bin', 'System Volume Information'}
            folders = [f for f in folders if f not in system_folders]
            
            print("   INFO: Detailed Folder Structure:")
            
            # Show important folders first with detailed content
            important_folders = ['data', 'logs', 'Logs', 'data_lidar_top', 'data_lidar_front']
            shown_folders = set()
            
            for folder in important_folders:
                if folder in folders:
                    print(f"   ├── FOLDER: {folder}/")
                    shown_folders.add(folder)
                    
                    # Show detailed subfolder structure for important folders
                    self._show_detailed_subfolder_structure(drive_path, folder, "   │   ", 1)
            
            # Show other folders with full hierarchy
            other_folders = [f for f in folders if f not in shown_folders and not f.startswith('.')]
            if other_folders:
                for i, folder in enumerate(other_folders):
                    is_last = (i == len(other_folders) - 1)
                    if is_last:
                        print(f"   └── FOLDER: {folder}/")
                        new_prefix = "       "
                    else:
                        print(f"   ├── FOLDER: {folder}/")
                        new_prefix = "   │   "
                    
                    # Show detailed subfolder structure for other folders
                    self._show_detailed_subfolder_structure(drive_path, folder, new_prefix, 1)
            
            # Show root directory files with types and examples
            if files:
                print(f"   └── [FILES] Root files ({len(files)} total):")
                self._show_file_types_and_examples(drive_path, files, "      ")
            
        except Exception as e:
            print(f"   ERROR: Error reading folder structure: {e}")
    
    def _show_detailed_subfolder_structure(self, drive_path: str, folder_name: str, prefix: str, depth: int = 0):
        """Show detailed subfolder structure with file types and examples - full hierarchy"""
        try:
            folder_path = os.path.join(drive_path, folder_name)
            if not os.path.exists(folder_path) or not os.access(folder_path, os.R_OK):
                print(f"{prefix}   (inaccessible)")
                return
            
            entries = os.listdir(folder_path)
            subfolders = [entry for entry in entries if os.path.isdir(os.path.join(folder_path, entry))]
            files = [entry for entry in entries if os.path.isfile(os.path.join(folder_path, entry))]
            
            # Filter out system folders
            system_folders = {'$RECYCLE.BIN', 'System Volume Information', '$Recycle.Bin', 'System Volume Information'}
            subfolders = [f for f in subfolders if f not in system_folders]
            
            # Apply simplification logic from depth 1 onwards (second level children become third level)
            if depth >= 1:  # depth 1 = second level, its children are third level
                if subfolders:
                    # Show only the first subfolder
                    subfolder = subfolders[0]
                    print(f"{prefix}└── FOLDER: {subfolder}/")
                    new_prefix = prefix + "    "
                    
                    # Recursively show this subfolder
                    self._show_full_folder_hierarchy(folder_path, subfolder, new_prefix, depth + 1)
                    
                    # Show count of other folders if there are more
                    if len(subfolders) > 1:
                        print(f"{prefix}    ... and {len(subfolders) - 1} more folders")
                else:
                    # Show files if no subfolders
                    if files:
                        print(f"{prefix}[FILES] Files ({len(files)} total):")
                        self._show_file_types_and_examples(folder_path, files, prefix + "   ")
                    else:
                        print(f"{prefix}(empty)")
            else:
                # Show all subfolders with full hierarchy
                for i, subfolder in enumerate(subfolders):
                    is_last = (i == len(subfolders) - 1)
                    if is_last:
                        print(f"{prefix}└── FOLDER: {subfolder}/")
                        new_prefix = prefix + "    "
                    else:
                        print(f"{prefix}├── FOLDER: {subfolder}/")
                        new_prefix = prefix + "│   "
                    
                    # Recursively show detailed content of this subfolder
                    self._show_full_folder_hierarchy(folder_path, subfolder, new_prefix, depth + 1)
            
            # Show files in this folder
            if files:
                if subfolders:
                    print(f"{prefix}└── [FILES] Files ({len(files)} total):")
                    self._show_file_types_and_examples(folder_path, files, prefix + "    ")
                else:
                    print(f"{prefix}[FILES] Files ({len(files)} total):")
                    self._show_file_types_and_examples(folder_path, files, prefix + "   ")
                
        except PermissionError:
            print(f"{prefix}   (access denied)")
        except Exception as e:
            print(f"{prefix}ERROR: Error reading subfolder: {e}")
    
    def _show_full_folder_hierarchy(self, parent_path: str, folder_name: str, prefix: str, depth: int = 0):
        """Show simplified folder hierarchy - from depth 3 onwards, show only one folder per level"""
        try:
            folder_path = os.path.join(parent_path, folder_name)
            if not os.path.exists(folder_path) or not os.access(folder_path, os.R_OK):
                print(f"{prefix}(inaccessible)")
                return
            
            entries = os.listdir(folder_path)
            subfolders = [entry for entry in entries if os.path.isdir(os.path.join(folder_path, entry))]
            files = [entry for entry in entries if os.path.isfile(os.path.join(folder_path, entry))]
            
            # Filter out system folders
            system_folders = {'$RECYCLE.BIN', 'System Volume Information', '$Recycle.Bin', 'System Volume Information'}
            subfolders = [f for f in subfolders if f not in system_folders]
            
            # From depth 2 onwards (third level), show only the first folder
            if depth >= 2:  # depth 2 = third level (0-indexed)
                if subfolders:
                    # Show only the first subfolder
                    subfolder = subfolders[0]
                    print(f"{prefix}└── FOLDER: {subfolder}/")
                    new_prefix = prefix + "    "
                    
                    # Recursively show this subfolder
                    self._show_full_folder_hierarchy(folder_path, subfolder, new_prefix, depth + 1)
                    
                    # Show count of other folders if there are more
                    if len(subfolders) > 1:
                        print(f"{prefix}    ... and {len(subfolders) - 1} more folders")
                else:
                    # Show files if no subfolders
                    if files:
                        print(f"{prefix}[FILES] Files ({len(files)} total):")
                        self._show_file_types_and_examples(folder_path, files, prefix + "   ")
                    else:
                        print(f"{prefix}(empty)")
            else:
                # For depths 0, 1, show all subfolders
                for i, subfolder in enumerate(subfolders):
                    is_last = (i == len(subfolders) - 1)
                    if is_last:
                        print(f"{prefix}└── FOLDER: {subfolder}/")
                        new_prefix = prefix + "    "
                    else:
                        print(f"{prefix}├── FOLDER: {subfolder}/")
                        new_prefix = prefix + "│   "
                    
                    # Recursively show this subfolder
                    self._show_full_folder_hierarchy(folder_path, subfolder, new_prefix, depth + 1)
                
                # Show files in this folder
                if files:
                    if subfolders:
                        print(f"{prefix}└── [FILES] Files ({len(files)} total):")
                        self._show_file_types_and_examples(folder_path, files, prefix + "    ")
                    else:
                        print(f"{prefix}[FILES] Files ({len(files)} total):")
                        self._show_file_types_and_examples(folder_path, files, prefix + "   ")
                elif not subfolders:
                    print(f"{prefix}(empty)")
                
        except PermissionError:
            print(f"{prefix}(access denied)")
        except Exception as e:
            print(f"{prefix}ERROR: Error: {e}")
    
    def _show_detailed_subfolder_content(self, parent_path: str, subfolder_name: str, prefix: str):
        """Show detailed content of a subfolder"""
        try:
            subfolder_path = os.path.join(parent_path, subfolder_name)
            if not os.path.exists(subfolder_path) or not os.access(subfolder_path, os.R_OK):
                print(f"{prefix}   (inaccessible)")
                return
            
            entries = os.listdir(subfolder_path)
            files = [entry for entry in entries if os.path.isfile(os.path.join(subfolder_path, entry))]
            
            if files:
                # Show file types and examples
                self._show_file_types_and_examples(subfolder_path, files, prefix)
            else:
                print(f"{prefix}   (empty)")
                
        except PermissionError:
            print(f"{prefix}   (access denied)")
        except Exception as e:
            print(f"{prefix}ERROR: Error reading subfolder content: {e}")
    
    def _show_basic_folder_info(self, drive_path: str, folder_name: str, prefix: str):
        """Show basic info for other folders"""
        try:
            folder_path = os.path.join(drive_path, folder_name)
            if not os.path.exists(folder_path) or not os.access(folder_path, os.R_OK):
                print(f"{prefix}   (inaccessible)")
                return
            
            entries = os.listdir(folder_path)
            files = [entry for entry in entries if os.path.isfile(os.path.join(folder_path, entry))]
            subfolders = [entry for entry in entries if os.path.isdir(os.path.join(folder_path, entry))]
            
            # Filter out system folders
            system_folders = {'$RECYCLE.BIN', 'System Volume Information', '$Recycle.Bin', 'System Volume Information'}
            subfolders = [f for f in subfolders if f not in system_folders]
            
            if files or subfolders:
                print(f"{prefix}   ({len(files)} files, {len(subfolders)} folders)")
            else:
                print(f"{prefix}   (empty)")
                
        except PermissionError:
            print(f"{prefix}   (access denied)")
        except Exception as e:
            print(f"{prefix}ERROR: Error reading folder info: {e}")
    
    def _show_file_types_and_examples(self, folder_path: str, files: list, prefix: str):
        """Show file types and example filenames"""
        try:
            if not files:
                return
            
            # Group files by extension
            file_groups = {}
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext not in file_groups:
                    file_groups[ext] = []
                file_groups[ext].append(file)
            
            # Show file types with examples
            shown_types = 0
            max_types = 5  # Show max 5 file types
            
            for ext, file_list in sorted(file_groups.items()):
                if shown_types >= max_types:
                    remaining_types = len(file_groups) - shown_types
                    print(f"{prefix}   ... and {remaining_types} more file types")
                    break
                
                if ext:
                    type_name = ext[1:].upper()  # Remove dot and uppercase
                else:
                    type_name = "NO_EXT"
                
                count = len(file_list)
                print(f"{prefix}   [FILE] {type_name} files ({count}): ", end="")
                
                # Show example filenames
                examples = file_list[:3]  # Show max 3 examples
                example_str = ", ".join(examples)
                if len(file_list) > 3:
                    example_str += f" ... (+{len(file_list) - 3} more)"
                
                print(example_str)
                shown_types += 1
                
        except Exception as e:
            print(f"{prefix}ERROR: Error showing file types: {e}")
    
    def _show_subfolder_structure(self, drive_path: str, folder_name: str, prefix: str):
        """Show subfolder structure for a specific folder (legacy method)"""
        try:
            folder_path = os.path.join(drive_path, folder_name)
            if not os.path.exists(folder_path):
                return
            
            entries = os.listdir(folder_path)
            subfolders = [entry for entry in entries if os.path.isdir(os.path.join(folder_path, entry))]
            
            # Show first few subfolders
            for i, subfolder in enumerate(subfolders[:3]):
                if i == len(subfolders) - 1 and len(subfolders) <= 3:
                    print(f"{prefix}└── FOLDER: {subfolder}/")
                else:
                    print(f"{prefix}├── FOLDER: {subfolder}/")
            
            if len(subfolders) > 3:
                print(f"{prefix}└── ... and {len(subfolders) - 3} more subfolders")
                
        except Exception as e:
            print(f"{prefix}ERROR: Error reading subfolder: {e}")
    
    def _show_detection_reason(self, drive_path: str, drive_type: str):
        """Show the reason why this drive was detected as the specific type"""
        try:
            print("   CHECKING: Detection Reason:")
            
            if drive_type == "Qdrive":
                # Check for specific Qdrive indicators
                if self._has_camera_fc_files(drive_path):
                    print("   ├── SUCCESS: Contains camera_fc*.mp4 files → Qdrive 201")
                elif self._has_camera_rc_files(drive_path):
                    print("   ├── SUCCESS: Contains camera_rc*.mp4 files → Qdrive 203")
                elif self._has_data_lidar_top(drive_path):
                    print("   ├── SUCCESS: Contains data_lidar_top folder → Qdrive 230")
                elif self._has_data_lidar_front(drive_path):
                    print("   ├── SUCCESS: Contains data_lidar_front folder → Qdrive 231")
                else:
                    print("   ├── [UNKNOWN] Detected as Qdrive but reason unclear")
            
            elif drive_type == "Vector":
                if self._has_logs_folder(drive_path):
                    print("   ├── SUCCESS: Contains Logs/logs folder → Vector drive")
                else:
                    print("   ├── [UNKNOWN] Detected as Vector but reason unclear")
            
            elif drive_type == "Backup":
                volume_name = self._get_volume_name(drive_path).lower()
                if volume_name.startswith('echo') and volume_name.endswith('backup'):
                    print("   ├── SUCCESS: Volume name: Echo*backup → Backup drive")
                else:
                    print("   ├── [UNKNOWN] Detected as Backup but reason unclear")
            
            elif drive_type == "Transfer":
                volume_name = self._get_volume_name(drive_path).lower()
                if volume_name.startswith('echo') and not volume_name.endswith('backup'):
                    print("   ├── SUCCESS: Volume name: Echo* (not backup) → Transfer drive")
                else:
                    print("   ├── [UNKNOWN] Detected as Transfer but reason unclear")
                    
        except Exception as e:
            print(f"   ERROR: Error showing detection reason: {e}")
    
    def _has_camera_fc_files(self, drive_path: str) -> bool:
        """Check if drive has camera_fc*.mp4 files"""
        try:
            for root, dirs, files in os.walk(drive_path):
                for file in files:
                    if file.startswith('camera_fc') and file.endswith('.mp4'):
                        return True
                if len(root.split(os.sep)) - len(drive_path.split(os.sep)) > 2:
                    dirs.clear()
            return False
        except:
            return False
    
    def _has_camera_rc_files(self, drive_path: str) -> bool:
        """Check if drive has camera_rc*.mp4 files"""
        try:
            for root, dirs, files in os.walk(drive_path):
                for file in files:
                    if file.startswith('camera_rc') and file.endswith('.mp4'):
                        return True
                if len(root.split(os.sep)) - len(drive_path.split(os.sep)) > 2:
                    dirs.clear()
            return False
        except:
            return False
    
    def _has_data_lidar_top(self, drive_path: str) -> bool:
        """Check if drive has data_lidar_top folder"""
        try:
            for root, dirs, files in os.walk(drive_path):
                if 'data_lidar_top' in dirs:
                    return True
                if len(root.split(os.sep)) - len(drive_path.split(os.sep)) > 2:
                    dirs.clear()
            return False
        except:
            return False
    
    def _has_data_lidar_front(self, drive_path: str) -> bool:
        """Check if drive has data_lidar_front folder"""
        try:
            for root, dirs, files in os.walk(drive_path):
                if 'data_lidar_front' in dirs:
                    return True
                if len(root.split(os.sep)) - len(drive_path.split(os.sep)) > 2:
                    dirs.clear()
            return False
        except:
            return False
    
    def _has_logs_folder(self, drive_path: str) -> bool:
        """Check if drive has Logs or logs folder"""
        try:
            entries = os.listdir(drive_path)
            return 'Logs' in entries or 'logs' in entries
        except:
            return False
    
    def _get_volume_name(self, drive_path: str) -> str:
        """Get volume name for a drive - using same method as drive_detector"""
        try:
            import platform
            import psutil
            
            os_type = platform.system().lower()
            
            if os_type == "windows":
                # 方法1: 尝试使用win32api
                try:
                    import win32api
                    volume_name = win32api.GetVolumeInformation(drive_path)[0]
                    if volume_name:
                        return volume_name
                except ImportError:
                    pass
                except (PermissionError, OSError):
                    pass
                
                # 方法2: 尝试使用subprocess调用Windows命令
                try:
                    import subprocess
                    result = subprocess.run(['wmic', 'logicaldisk', 'where', f'DeviceID="{drive_path[:-1]}"', 'get', 'VolumeName', '/value'], 
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
                        if partition.device == drive_path and hasattr(partition, 'label') and partition.label:
                            return partition.label
                except Exception:
                    pass
                
                # 方法4: 使用盘符作为备选
                return f"Drive_{drive_path[:-1]}"
            else:
                # Linux/macOS系统：使用路径名
                return os.path.basename(drive_path.rstrip('/'))
                
        except Exception as e:
            logger.debug(f"Error getting volume name for {drive_path}: {e}")
            return ""
