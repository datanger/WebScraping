#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进度条工具模块
Progress Bar Utility Module
"""

import time
import logging

logger = logging.getLogger(__name__)

# 尝试导入进度条库，如果没有则使用简单版本
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("提示: 安装 tqdm 库可以获得更好的进度条显示: pip install tqdm")

def create_progress_bar(total: int, desc: str):
    """
    创建进度条对象
    
    Args:
        total: 总数量
        desc: 描述文字
        
    Returns:
        object: 进度条对象
    """
    if HAS_TQDM:
        return tqdm(total=total, desc=desc, unit='file', ncols=80)
    else:
        # 简单的进度显示
        return SimpleProgressBar(total, desc)

def update_progress(progress_bar, amount: int = 1):
    """
    更新进度条
    
    Args:
        progress_bar: 进度条对象
        amount: 增加的数量
    """
    if HAS_TQDM:
        progress_bar.update(amount)
    else:
        progress_bar.update(amount)

def close_progress(progress_bar):
    """
    关闭进度条
    
    Args:
        progress_bar: 进度条对象
    """
    if HAS_TQDM:
        progress_bar.close()
    else:
        progress_bar.close()

class SimpleProgressBar:
    """简单的进度条实现（当tqdm不可用时使用）"""
    
    def __init__(self, total: int, desc: str):
        self.total = total
        self.desc = desc
        self.current = 0
        self.start_time = time.time()
        self.last_update = 0
        
    def update(self, amount: int = 1):
        self.current += amount
        current_time = time.time()
        
        # 每2秒最多更新一次显示，减少闪烁
        if current_time - self.last_update >= 2.0 or self.current >= self.total:
            self._display_progress()
            self.last_update = current_time
    
    def _display_progress(self):
        if self.total > 0:
            percentage = (self.current / self.total) * 100
            elapsed_time = time.time() - self.start_time
            
            if self.current > 0:
                estimated_total = elapsed_time * self.total / self.current
                remaining_time = estimated_total - elapsed_time
                eta_str = f"ETA: {remaining_time:.1f}s"
            else:
                eta_str = "ETA: --"
            
            # 创建进度条
            bar_length = 30
            filled_length = int(bar_length * self.current // self.total)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            # 使用更稳定的显示方式，避免闪烁
            print(f"\r{self.desc}: [{bar}] {percentage:5.1f}% ({self.current}/{self.total}) {eta_str}", end='', flush=True)
            
            if self.current >= self.total:
                print()  # 换行
    
    def close(self):
        if self.current < self.total:
            self._display_progress()
        print()  # 确保换行 