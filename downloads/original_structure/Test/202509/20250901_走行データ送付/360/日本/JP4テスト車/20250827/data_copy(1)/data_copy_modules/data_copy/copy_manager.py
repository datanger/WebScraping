#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copy Manager Module
"""

import logging
from typing import List

logger = logging.getLogger(__name__)

class CopyManager:
    """Copy Manager Class"""
    
    def __init__(self):
        """Initialize copy manager"""
        pass
    
    def plan_copy_operations(self, qdrive_drives: List[str], vector_drives: List[str], 
                           transfer_drives: List[str], backup_drives: List[str]) -> dict:
        """
        Plan copy operations
        
        Args:
            qdrive_drives: Qdrive source drive list
            vector_drives: Vector source drive list
            transfer_drives: Transfer target drive list
            backup_drives: Backup target drive list
            
        Returns:
            dict: Copy plan
        """
        copy_plan = {
            'transfer_operations': [],
            'backup_operations': [],
            'total_files': 0,
            'total_size': 0
        }
        
        # 规划Transfer盘拷贝操作
        if transfer_drives:
            transfer_drive = transfer_drives[0]
            
            # Qdrive数据拷贝到Transfer
            for qdrive_drive in qdrive_drives:
                copy_plan['transfer_operations'].append({
                    'type': 'qdrive',
                    'source': qdrive_drive,
                    'destination': transfer_drive,
                    'operation': 'copy_qdrive_data_to_transfer'
                })
            
            # Vector数据拷贝到Transfer
            for vector_drive in vector_drives:
                copy_plan['transfer_operations'].append({
                    'type': 'vector',
                    'source': vector_drive,
                    'destination': transfer_drive,
                    'operation': 'copy_vector_data_to_transfer'
                })
        
        # 规划Backup盘拷贝操作
        if backup_drives:
            backup_drive = backup_drives[0]
            
            # Vector数据拷贝到Backup
            for vector_drive in vector_drives:
                copy_plan['backup_operations'].append({
                    'type': 'vector',
                    'source': vector_drive,
                    'destination': backup_drive,
                    'operation': 'copy_vector_data_to_backup'
                })
            
            # Qdrive数据拷贝到Backup
            for qdrive_drive in qdrive_drives:
                copy_plan['backup_operations'].append({
                    'type': 'qdrive',
                    'source': qdrive_drive,
                    'destination': backup_drive,
                    'operation': 'copy_qdrive_data_to_backup'
                })
        
        logger.info(f"拷贝计划生成完成:")
        logger.info(f"  Transfer操作: {len(copy_plan['transfer_operations'])} 个")
        logger.info(f"  Backup操作: {len(copy_plan['backup_operations'])} 个")
        
        return copy_plan
    
    def validate_copy_plan(self, copy_plan: dict) -> bool:
        """
        验证拷贝计划
        
        Args:
            copy_plan: 拷贝计划
            
        Returns:
            bool: 计划是否有效
        """
        try:
            # 检查是否有源盘
            if not copy_plan['transfer_operations'] and not copy_plan['backup_operations']:
                logger.error("拷贝计划中没有操作")
                return False
            
            # 检查源盘和目标盘是否有效
            for operation in copy_plan['transfer_operations'] + copy_plan['backup_operations']:
                if not operation['source'] or not operation['destination']:
                    logger.error(f"拷贝操作配置无效: {operation}")
                    return False
            
            logger.info("拷贝计划验证通过")
            return True
            
        except Exception as e:
            logger.error(f"验证拷贝计划时出错: {e}")
            return False
    
    def execute_copy_plan(self, copy_plan: dict, detector) -> bool:
        """
        执行拷贝计划
        
        Args:
            copy_plan: 拷贝计划
            detector: 系统检测器实例
            
        Returns:
            bool: 执行是否成功
        """
        try:
            logger.info("开始执行拷贝计划")
            
            # 执行Transfer盘拷贝操作
            if copy_plan['transfer_operations']:
                logger.info("执行Transfer盘拷贝操作...")
                for operation in copy_plan['transfer_operations']:
                    if operation['type'] == 'qdrive':
                        success = detector.copy_qdrive_data_to_transfer(
                            operation['source'], operation['destination']
                        )
                    elif operation['type'] == 'vector':
                        success = detector.copy_vector_data_to_transfer(
                            operation['source'], operation['destination']
                        )
                    
                    if not success:
                        logger.error(f"拷贝操作失败: {operation}")
                        return False
            
            # 执行Backup盘拷贝操作
            if copy_plan['backup_operations']:
                logger.info("执行Backup盘拷贝操作...")
                
                # 先创建Qdrive数据的目录结构
                qdrive_drives = [op['source'] for op in copy_plan['backup_operations'] 
                               if op['type'] == 'qdrive']
                if qdrive_drives:
                    backup_drive = copy_plan['backup_operations'][0]['destination']
                    if not detector.create_backup_directory_structure(backup_drive, qdrive_drives):
                        logger.error("创建Backup目录结构失败")
                        return False
                
                # 执行拷贝操作
                for operation in copy_plan['backup_operations']:
                    if operation['type'] == 'qdrive':
                        success = detector.copy_qdrive_data_to_backup(
                            operation['source'], operation['destination']
                        )
                    elif operation['type'] == 'vector':
                        success = detector.copy_vector_data_to_backup(
                            operation['source'], operation['destination']
                        )
                    
                    if not success:
                        logger.error(f"拷贝操作失败: {operation}")
                        return False
            
            logger.info("拷贝计划执行完成")
            return True
            
        except Exception as e:
            logger.error(f"执行拷贝计划时出错: {e}")
            return False 