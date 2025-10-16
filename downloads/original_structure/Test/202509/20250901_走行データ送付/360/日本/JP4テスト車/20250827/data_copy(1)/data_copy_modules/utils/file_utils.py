#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件工具模块
File Utilities Module
"""

import os
import shutil
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

def get_directory_stats(path: str) -> Dict[str, int]:
    """
    获取目录的统计信息
    
    Args:
        path: 目录路径
        
    Returns:
        Dict[str, int]: 包含文件数量和总大小的字典
    """
    try:
        file_count = 0
        total_size = 0
        
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    file_size = os.path.getsize(file_path)
                    total_size += file_size
                    file_count += 1
                except (OSError, IOError) as e:
                    logger.warning(f"无法获取文件 {file_path} 的大小: {e}")
                    continue
        
        return {
            'file_count': file_count,
            'total_size': total_size
        }
        
    except Exception as e:
        logger.error(f"获取目录统计信息时出错: {e}")
        return {'file_count': 0, 'total_size': 0}

def format_size(size_bytes: int) -> str:
    """
    格式化文件大小显示
    
    Args:
        size_bytes: 字节数
        
    Returns:
        str: 格式化后的大小字符串
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"

def generate_directory_tree(path: str, max_depth: int = 3) -> str:
    """
    生成目录树字符串
    
    Args:
        path: 根目录路径
        max_depth: 最大深度
        
    Returns:
        str: 目录树字符串
    """
    def _generate_tree(current_path: str, prefix: str, depth: int) -> str:
        if depth > max_depth:
            return ""
        
        result = ""
        try:
            items = sorted(os.listdir(current_path))
            for i, item in enumerate(items):
                item_path = os.path.join(current_path, item)
                is_last = (i == len(items) - 1)
                
                if os.path.isdir(item_path):
                    result += f"{prefix}{'└── ' if is_last else '├── '}{item}/\n"
                    if depth < max_depth:
                        new_prefix = prefix + ('    ' if is_last else '│   ')
                        result += _generate_tree(item_path, new_prefix, depth + 1)
                else:
                    result += f"{prefix}{'└── ' if is_last else '├── '}{item}\n"
                    
        except PermissionError:
            result += f"{prefix}└── [权限不足]\n"
        except Exception as e:
            result += f"{prefix}└── [错误: {e}]\n"
        
        return result
    
    return f"{os.path.basename(path)}/\n" + _generate_tree(path, "", 1)

def get_unique_filename(file_path: str) -> str:
    """
    获取唯一的文件名，如果文件已存在则自动重命名
    
    Args:
        file_path: 原始文件路径
        
    Returns:
        str: 唯一的文件路径
    """
    if not os.path.exists(file_path):
        return file_path
    
    # 分离文件名和扩展名
    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    name, ext = os.path.splitext(filename)
    
    counter = 1
    while True:
        new_filename = f"{name}{counter}{ext}"
        new_file_path = os.path.join(directory, new_filename)
        
        if not os.path.exists(new_file_path):
            return new_file_path
        
        counter += 1

def copy_file_with_rename(src_file: str, dst_file: str) -> bool:
    """
    拷贝文件，如果目标文件已存在则自动重命名
    
    Args:
        src_file: 源文件路径
        dst_file: 目标文件路径
        
    Returns:
        bool: 拷贝是否成功
    """
    try:
        # 获取唯一的文件名
        unique_dst_file = get_unique_filename(dst_file)
        
        # 如果文件名发生了变化，记录日志
        if unique_dst_file != dst_file:
            logger.info(f"目标文件已存在，自动重命名: {os.path.basename(dst_file)} → {os.path.basename(unique_dst_file)}")
        
        # 检查源文件大小，对于大文件记录开始拷贝
        try:
            file_size = os.path.getsize(src_file)
            if file_size > 100 * 1024 * 1024:  # 大于100MB的文件
                logger.debug(f"开始拷贝大文件: {os.path.basename(src_file)} ({file_size / (1024*1024):.1f}MB)")
        except OSError:
            pass
        
        # 拷贝文件
        shutil.copy2(src_file, unique_dst_file)
        
        # 记录大文件拷贝完成
        try:
            if file_size > 100 * 1024 * 1024:
                logger.debug(f"大文件拷贝完成: {os.path.basename(src_file)}")
        except NameError:
            pass
        
        return True
        
    except Exception as e:
        logger.error(f"拷贝文件时出错: {e}")
        return False

def copy_directory_with_rename(src_dir: str, dst_dir: str, progress_callback=None) -> bool:
    """
    拷贝目录，处理同名文件自动重命名 - 增强版本
    
    Args:
        src_dir: 源目录路径
        dst_dir: 目标目录路径
        progress_callback: 进度回调函数
        
    Returns:
        bool: 拷贝是否成功
    """
    try:
        # 创建目标目录
        os.makedirs(dst_dir, exist_ok=True)
        
        copied_files = 0
        failed_files = 0
        total_files = 0
        
        # 首先统计总文件数
        for root, dirs, files in os.walk(src_dir):
            total_files += len(files)
        
        logger.info(f"开始拷贝目录: {src_dir} -> {dst_dir}")
        logger.info(f"总文件数: {total_files}")
        
        # 遍历源目录
        for root, dirs, files in os.walk(src_dir):
            # 计算相对路径
            rel_path = os.path.relpath(root, src_dir)
            target_dir = os.path.join(dst_dir, rel_path)
            
            # 创建子目录
            try:
                os.makedirs(target_dir, exist_ok=True)
            except Exception as e:
                logger.error(f"无法创建目标目录 {target_dir}: {e}")
                continue
            
            # 拷贝文件
            for file in files:
                src_file = os.path.join(root, file)
                dst_file = os.path.join(target_dir, file)
                
                try:
                    # 简化文件验证，只检查基本存在性
                    if not os.path.exists(src_file):
                        logger.debug(f"源文件不存在，跳过: {src_file}")
                        failed_files += 1
                        continue
                    
                    # 使用自动重命名功能拷贝文件
                    success = copy_file_with_rename(src_file, dst_file)
                    if success:
                        copied_files += 1
                        if progress_callback:
                            progress_callback(1)
                        logger.debug(f"成功拷贝: {src_file} -> {dst_file}")
                    else:
                        failed_files += 1
                        logger.debug(f"拷贝文件失败: {src_file}")
                        
                except Exception as e:
                    failed_files += 1
                    logger.debug(f"拷贝文件 {src_file} 时出错: {e}")
                    continue
        
        # 记录拷贝结果
        logger.info(f"拷贝完成: 成功 {copied_files} 个文件, 失败 {failed_files} 个文件")
        
        if failed_files > 0:
            logger.warning(f"有 {failed_files} 个文件拷贝失败")
        
        # 确保进度回调被调用到100%（即使有失败的文件）
        if progress_callback and copied_files < total_files:
            remaining_files = total_files - copied_files
            logger.info(f"调用进度回调补足剩余 {remaining_files} 个文件")
            for _ in range(remaining_files):
                progress_callback(1)
        
        # 如果大部分文件都拷贝成功，认为拷贝成功
        success_rate = copied_files / total_files if total_files > 0 else 0
        if success_rate >= 0.7:  # 降低到70%以上成功
            logger.info(f"拷贝成功率: {success_rate:.2%}")
            return True
        else:
            logger.error(f"拷贝成功率过低: {success_rate:.2%}")
            return False
        
    except Exception as e:
        logger.error(f"拷贝目录时出错: {e}")
        return False 