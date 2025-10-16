#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vector数据处理模块
Vector Data Handler Module
"""

import os
import re
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

class VectorDataHandler:
    """Vector数据处理器类"""
    
    def __init__(self):
        """初始化Vector数据处理器"""
        pass
    
    def check_vector_data_dates(self, vector_drive: str) -> Tuple[bool, List[str]]:
        """
        检查Vector数据盘中的日期数量
        
        Args:
            vector_drive: Vector数据盘路径
            
        Returns:
            Tuple[bool, List[str]]: (是否只有一个日期, 日期列表)
        """
        try:
            logs_path = os.path.join(vector_drive, 'logs')
            if not os.path.exists(logs_path):
                return False, []
            
            dates = set()
            for root, dirs, files in os.walk(logs_path):
                for dir_name in dirs:
                    # 检查是否为日期格式 (yyyymmdd_hhmmss)
                    if re.match(r'\d{8}_\d{6}', dir_name):
                        date_part = dir_name[:8]  # 提取日期部分
                        dates.add(date_part)
                    elif re.match(r'\d{4}_\d{2}_\d{2}-\d{2}_\d{2}', dir_name):
                        # 兼容其他日期格式
                        date_part = dir_name[:10]
                        dates.add(date_part)
            
            date_list = sorted(list(dates))
            is_single_date = len(date_list) == 1
            
            logger.info(f"Vector数据盘 {vector_drive} 包含 {len(date_list)} 个日期: {date_list}")
            
            return is_single_date, date_list
            
        except Exception as e:
            logger.error(f"检查Vector数据盘 {vector_drive} 日期时出错: {e}")
            return False, [] 