#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据拷贝模块包
Data Copy Modules Package

包含以下子模块：
- core: 核心系统检测功能
- drivers: 驱动器管理功能
- data_copy: 数据拷贝功能
- utils: 工具函数
- logging: 日志管理功能
"""

__version__ = "1.0.0"
__author__ = "Data Copy Team"

from .core import CrossPlatformSystemDetector
from .logging_utils import setup_copy_logger, COPY_LOG_FILE, FILELIST_LOG_FILE

__all__ = [
    'CrossPlatformSystemDetector',
    'setup_copy_logger',
    'COPY_LOG_FILE',
    'FILELIST_LOG_FILE'
] 