#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qdrive Data Handler Module
"""

import os
import re
import datetime
import logging
from typing import List

logger = logging.getLogger(__name__)

class QdriveDataHandler:
    """Qdrive data handler class"""
    
    def __init__(self):
        """Initialize Qdrive data handler"""
        self.backup_disk_type = None  # Save A/B disk selection result
        self.backup_root_dir = None   # Save backup root directory path
    
    def extract_vehicle_model(self, vehicle_id: str) -> str:
        """
        Extract vehicle model from vehicle ID
        
        Args:
            vehicle_id: Vehicle ID (e.g.: 3NRV1_201)
            
        Returns:
            str: Vehicle model (e.g.: RV1)
        """
        try:
            # Match vehicle model pattern: combination of letters and numbers
            match = re.search(r'([A-Z]+\d+)', vehicle_id)
            if match:
                return match.group(1)
            else:
                # If no match found, return part of the vehicle ID
                return vehicle_id.split('_')[0] if '_' in vehicle_id else vehicle_id
        except Exception:
            return vehicle_id
    
    def create_backup_directory_structure(self, backup_drive: str, qdrive_drives: List[str]) -> bool:
        """
        Create Qdrive data directory structure in backup drive
        
        Args:
            backup_drive: Backup target drive path
            qdrive_drives: Qdrive source drive list
            
        Returns:
            bool: Whether creation was successful
        """
        try:
            if not qdrive_drives:
                logger.error("No available Qdrive data drives")
                return False
            
            # Extract vehicle model and date information from Qdrive data
            all_vehicle_models = set()
            all_dates = set()
            
            # Silently analyze Qdrive data structure
            for qdrive_drive in qdrive_drives:
                data_path = os.path.join(qdrive_drive, 'data')
                
                if os.path.exists(data_path):
                    try:
                        # Traverse second-level directories (vehicle model directories)
                        vehicle_dirs = os.listdir(data_path)
                        
                        for vehicle_dir in vehicle_dirs:
                            vehicle_path = os.path.join(data_path, vehicle_dir)
                            
                            if os.path.isdir(vehicle_path):
                                # Extract vehicle model: extract RV1 from 2qd_3NRV1_v1
                                vehicle_model = vehicle_dir
                                # Use regex to extract RV1 part
                                rv_match = re.search(r'3N([A-Z]+\d+)', vehicle_dir)
                                if rv_match:
                                    vehicle_model = rv_match.group(1)  # Extract RV1
                                else:
                                    # If no match for 3N+alphanumeric pattern, try other methods
                                    if 'RV1' in vehicle_dir:
                                        vehicle_model = 'RV1'
                                    else:
                                        continue
                                
                                all_vehicle_models.add(vehicle_model)
                                
                                try:
                                    # Traverse third-level directories (date directories)
                                    date_dirs = os.listdir(vehicle_path)
                                    
                                    for date_dir in date_dirs:
                                        date_path = os.path.join(vehicle_path, date_dir)
                                        
                                        if os.path.isdir(date_path):
                                            # Extract 20250821 from 2025_08_21-10_19
                                            date_match = re.search(r'(\d{4})_(\d{2})_(\d{2})', date_dir)
                                            if date_match:
                                                year, month, day = date_match.groups()
                                                extracted_date = f"{year}{month}{day}"
                                                all_dates.add(extracted_date)
                                except Exception as e:
                                    logger.warning(f"Error reading third-level directory: {e}")
                    except Exception as e:
                        logger.warning(f"Error reading second-level directory: {e}")
            
            if not all_vehicle_models:
                logger.error("Unable to get vehicle model information from Qdrive data")
                return False
            
            if not all_dates:
                logger.error("Unable to get date information from Qdrive data")
                print("\nTrying to use current system date as fallback...")
                current_date = datetime.datetime.now().strftime("%Y%m%d")
                all_dates.add(current_date)
                print(f"Using current system date: {current_date}")
            
            # Display detected information
            print(f"\nDetected vehicle models: {', '.join(sorted(all_vehicle_models))}")
            print(f"Detected dates: {', '.join(sorted(all_dates))}")
            
            # Automatically select main vehicle model and date (for root directory naming)
            if len(all_vehicle_models) == 1:
                main_vehicle_model = list(all_vehicle_models)[0]
            else:
                # Automatically select first vehicle model
                main_vehicle_model = sorted(all_vehicle_models)[0]
            
            if len(all_dates) == 1:
                main_date = list(all_dates)[0]
            else:
                # Automatically select first date
                main_date = sorted(all_dates)[0]
            
            # Create root directory: date-vehicle_model
            root_dir_name = f"{main_date}-{main_vehicle_model}"
            root_dir_path = os.path.join(backup_drive, root_dir_name)
            
            # Use suggested root directory name directly
            print(f"Using root directory name: {root_dir_name}")
            
            # User selects A or B disk
            while True:
                disk_choice = input("Please select A or B disk (A/B): ").strip().upper()
                if disk_choice in ['A', 'B']:
                    break
                else:
                    print("ERROR: Invalid selection, please enter A or B")
            
            # Create root directory
            os.makedirs(root_dir_path, exist_ok=True)
            
            # Create corresponding second-level directories based on selected Qdrive drive numbers
            # Use passed qdrive_drives and expected drive number mapping
            expected_drive_numbers = ['201', '203', '230', '231']
            
            # Create corresponding second-level directories for each vehicle model and drive number
            for vehicle_model in sorted(all_vehicle_models):
                for drive_number in expected_drive_numbers:
                    # Ensure vehicle model name includes 3N prefix
                    if not vehicle_model.startswith('3N'):
                        vehicle_model_with_prefix = f"3N{vehicle_model}"
                    else:
                        vehicle_model_with_prefix = vehicle_model
                    
                    subdir_name = f"{vehicle_model_with_prefix}_{drive_number}_{disk_choice}"
                    subdir_path = os.path.join(root_dir_path, subdir_name)
                    os.makedirs(subdir_path, exist_ok=True)
                    logger.info(f"Created second-level directory: {subdir_path}")
            
            logger.info(f"Successfully created directory structure in backup drive {backup_drive}")
            logger.info(f"Contains vehicle models: {', '.join(sorted(all_vehicle_models))}")
            logger.info(f"Contains dates: {', '.join(sorted(all_dates))}")
            logger.info(f"Contains drive numbers: {', '.join(expected_drive_numbers)}")
            logger.info(f"Selected disk type: {disk_choice} disk")
            
            # Save A/B disk selection result for subsequent copy operations
            self.backup_disk_type = disk_choice
            self.backup_root_dir = root_dir_path
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating backup drive directory structure: {e}")
            return False 