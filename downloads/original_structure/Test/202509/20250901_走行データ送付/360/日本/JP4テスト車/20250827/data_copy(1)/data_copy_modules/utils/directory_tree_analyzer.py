#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
目录结构分析器模块
Directory Tree Analyzer Module
"""

import os
import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class DirectoryTreeAnalyzer:
    """目录结构分析器类"""
    
    def __init__(self, max_depth: int = 3, max_items_per_level: int = 5):
        """
        初始化目录结构分析器
        
        Args:
            max_depth: 最大分析深度
            max_items_per_level: 每层最大显示项目数
        """
        self.max_depth = max_depth
        self.max_items_per_level = max_items_per_level
        
        # 重要文件扩展名
        self.important_extensions = ['.mp4', '.log', '.txt', '.json', '.xml', '.bin', '.dat']
        
        # 重要文件前缀
        self.important_prefixes = ['camera_', 'data_', 'lidar_', 'system_', 'error_']
        
        # 重要文件夹名称
        self.important_folders = ['data', 'logs', 'Logs', 'data_lidar_top', 'data_lidar_front']
    
    def analyze_drive_structure(self, drive_path: str) -> Dict[str, Any]:
        """
        分析驱动器目录结构
        
        Args:
            drive_path: 驱动器路径
            
        Returns:
            Dict[str, Any]: 目录结构信息
        """
        try:
            structure = {
                'drive_path': drive_path,
                'drive_name': os.path.basename(drive_path.rstrip(os.sep)),
                'folders': [],
                'files': [],
                'total_size': 0,
                'file_count': 0,
                'folder_count': 0,
                'analysis_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            if not os.path.exists(drive_path):
                structure['error'] = f"Drive path does not exist: {drive_path}"
                return structure
            
            if not os.access(drive_path, os.R_OK):
                structure['error'] = f"No read permission for: {drive_path}"
                return structure
            
            # 分析根目录
            try:
                entries = os.listdir(drive_path)
                entries.sort()  # 排序以便显示
                
                for item in entries:
                    item_path = os.path.join(drive_path, item)
                    
                    if os.path.isdir(item_path):
                        # 分析子目录
                        sub_structure = self._analyze_subdirectory(item_path, self.max_depth - 1)
                        structure['folders'].append(sub_structure)
                        structure['folder_count'] += 1
                    else:
                        # 记录文件信息
                        file_info = self._get_file_info(item_path)
                        structure['files'].append(file_info)
                        structure['total_size'] += file_info['size']
                        structure['file_count'] += 1
                        
            except PermissionError as e:
                structure['error'] = f"Permission denied: {e}"
            except Exception as e:
                structure['error'] = f"Error analyzing directory: {e}"
                
        except Exception as e:
            structure = {
                'drive_path': drive_path,
                'error': f"Failed to analyze drive: {e}"
            }
        
        return structure
    
    def _analyze_subdirectory(self, path: str, remaining_depth: int) -> Dict[str, Any]:
        """
        分析子目录结构
        
        Args:
            path: 目录路径
            remaining_depth: 剩余分析深度
            
        Returns:
            Dict[str, Any]: 子目录结构信息
        """
        structure = {
            'path': path,
            'name': os.path.basename(path),
            'type': 'folder',
            'subfolders': [],
            'files': [],
            'size': 0,
            'file_count': 0,
            'is_important': self._is_important_folder(os.path.basename(path))
        }
        
        if remaining_depth <= 0:
            return structure
        
        try:
            entries = os.listdir(path)
            entries.sort()
            
            for item in entries:
                item_path = os.path.join(path, item)
                
                if os.path.isdir(item_path):
                    sub_structure = self._analyze_subdirectory(item_path, remaining_depth - 1)
                    structure['subfolders'].append(sub_structure)
                else:
                    file_info = self._get_file_info(item_path)
                    structure['files'].append(file_info)
                    structure['size'] += file_info['size']
                    structure['file_count'] += 1
                    
        except (PermissionError, OSError) as e:
            structure['error'] = f"Access error: {e}"
        except Exception as e:
            structure['error'] = f"Analysis error: {e}"
        
        return structure
    
    def _get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        获取文件信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict[str, Any]: 文件信息
        """
        try:
            stat = os.stat(file_path)
            filename = os.path.basename(file_path)
            
            return {
                'name': filename,
                'path': file_path,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                'is_important': self._is_important_file(filename)
            }
        except Exception as e:
            return {
                'name': os.path.basename(file_path),
                'path': file_path,
                'size': 0,
                'error': str(e),
                'is_important': False
            }
    
    def _is_important_file(self, filename: str) -> bool:
        """
        判断是否为重要文件
        
        Args:
            filename: 文件名
            
        Returns:
            bool: 是否为重要文件
        """
        filename_lower = filename.lower()
        
        # 检查扩展名
        if any(filename_lower.endswith(ext) for ext in self.important_extensions):
            return True
        
        # 检查前缀
        if any(filename_lower.startswith(prefix) for prefix in self.important_prefixes):
            return True
        
        return False
    
    def _is_important_folder(self, folder_name: str) -> bool:
        """
        判断是否为重要文件夹
        
        Args:
            folder_name: 文件夹名称
            
        Returns:
            bool: 是否为重要文件夹
        """
        return folder_name in self.important_folders
    
    def generate_simple_directory_tree(self, structure: Dict[str, Any], indent: int = 0) -> List[str]:
        """
        生成简易目录树
        
        Args:
            structure: 目录结构信息
            indent: 缩进级别
            
        Returns:
            List[str]: 目录树文本行
        """
        tree_lines = []
        prefix = "  " * indent
        
        # 检查是否有错误
        if 'error' in structure:
            error_line = f"{prefix}ERROR: Error: {structure['error']}"
            tree_lines.append(error_line)
            return tree_lines
        
        # 显示驱动器信息（根级别）
        if indent == 0:
            drive_info = self._format_drive_info(structure)
            tree_lines.append(drive_info)
        
        # 显示文件夹
        folders_to_show = structure.get('folders', [])[:self.max_items_per_level]
        for folder in folders_to_show:
            folder_line = self._format_folder_info(folder, prefix)
            tree_lines.append(folder_line)
            
            # 递归显示子文件夹（限制深度）
            if indent < self.max_depth - 1:
                sub_tree = self.generate_simple_directory_tree(folder, indent + 1)
                tree_lines.extend(sub_tree)
        
        # 显示重要文件
        all_files = structure.get('files', [])
        important_files = [f for f in all_files if f.get('is_important', False)]
        regular_files = [f for f in all_files if not f.get('is_important', False)]
        
        # 显示重要文件
        for file_info in important_files[:3]:  # 限制显示数量
            file_line = self._format_file_info(file_info, prefix)
            tree_lines.append(file_line)
        
        # 显示部分常规文件
        for file_info in regular_files[:2]:  # 限制显示数量
            file_line = self._format_file_info(file_info, prefix)
            tree_lines.append(file_line)
        
        # 如果有更多文件，显示省略号
        total_files = len(all_files)
        shown_files = len(important_files[:3]) + len(regular_files[:2])
        if total_files > shown_files:
            more_count = total_files - shown_files
            tree_lines.append(f"{prefix}... ({more_count} more files)")
        
        # 如果有更多文件夹，显示省略号
        total_folders = len(structure.get('folders', []))
        if total_folders > self.max_items_per_level:
            more_folders = total_folders - self.max_items_per_level
            tree_lines.append(f"{prefix}... ({more_folders} more folders)")
        
        return tree_lines
    
    def _format_drive_info(self, structure: Dict[str, Any]) -> str:
        """
        格式化驱动器信息
        
        Args:
            structure: 驱动器结构信息
            
        Returns:
            str: 格式化的驱动器信息
        """
        drive_path = structure['drive_path']
        total_size = self._format_size(structure.get('total_size', 0))
        file_count = structure.get('file_count', 0)
        folder_count = structure.get('folder_count', 0)
        
        return f"INFO: {drive_path} ({total_size}, {file_count} files, {folder_count} folders)"
    
    def _format_folder_info(self, folder: Dict[str, Any], prefix: str) -> str:
        """
        格式化文件夹信息
        
        Args:
            folder: 文件夹信息
            prefix: 前缀字符串
            
        Returns:
            str: 格式化的文件夹信息
        """
        folder_name = folder['name']
        file_count = folder.get('file_count', 0)
        size = self._format_size(folder.get('size', 0))
        
        # 重要文件夹使用特殊图标
        icon = "IMPORTANT:" if folder.get('is_important', False) else "FOLDER:"
        
        if file_count > 0:
            return f"{prefix}{icon} {folder_name}/ ({size}, {file_count} files)"
        else:
            return f"{prefix}{icon} {folder_name}/"
    
    def _format_file_info(self, file_info: Dict[str, Any], prefix: str) -> str:
        """
        格式化文件信息
        
        Args:
            file_info: 文件信息
            prefix: 前缀字符串
            
        Returns:
            str: 格式化的文件信息
        """
        filename = file_info['name']
        size = self._format_size(file_info.get('size', 0))
        
        # 重要文件使用特殊图标
        icon = "[IMPORTANT]" if file_info.get('is_important', False) else "[FILE]"
        
        return f"{prefix}{icon} {filename} ({size})"
    
    def _format_size(self, size_bytes: int) -> str:
        """
        格式化文件大小
        
        Args:
            size_bytes: 字节数
            
        Returns:
            str: 格式化的文件大小
        """
        if size_bytes == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.1f} {units[unit_index]}"
    
    def analyze_multiple_drives(self, drives: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        分析多个驱动器
        
        Args:
            drives: 驱动器路径列表
            
        Returns:
            Dict[str, Dict[str, Any]]: 驱动器分析结果
        """
        results = {}
        
        for drive in drives:
            logger.info(f"Analyzing drive structure: {drive}")
            structure = self.analyze_drive_structure(drive)
            results[drive] = structure
        
        return results
