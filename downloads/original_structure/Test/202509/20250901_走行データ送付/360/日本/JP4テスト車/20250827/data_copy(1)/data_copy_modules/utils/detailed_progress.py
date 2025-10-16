#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detailed Progress Display Module
显示每个驱动器拷贝进度的详细进度条
"""

import time
import threading
import os
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class DetailedProgressTracker:
    """详细进度跟踪器 - 跟踪每个驱动器的拷贝进度"""
    
    def __init__(self, refresh_interval: int = 30):
        """
        初始化进度跟踪器
        
        Args:
            refresh_interval: 刷新间隔（秒），默认30秒
        """
        self.refresh_interval = refresh_interval
        self.tasks = {}  # 存储所有任务信息
        self.start_time = time.time()
        self.last_update = 0
        self.lock = threading.Lock()
        self.running = True
        self.last_display_time = 0  # 记录上次显示时间
        self.display_count = 0  # 显示次数计数器
        self.is_displaying = False  # 防止重复显示
        
        # 启动显示线程
        self.display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self.display_thread.start()
    
    def add_task(self, task_id: str, source: str, target: str, total_files: int = 0):
        """
        添加新任务
        
        Args:
            task_id: 任务ID
            source: 源路径
            target: 目标路径
            total_files: 总文件数
        """
        with self.lock:
            self.tasks[task_id] = {
                'source': source,
                'target': target,
                'total_files': total_files,
                'copied_files': 0,
                'start_time': time.time(),
                'status': 'running',  # running, completed, failed
                'last_update': time.time()
            }
    
    def update_task(self, task_id: str, copied_files: int, status: str = 'running', total_files: int = None):
        """
        更新任务进度
        
        Args:
            task_id: 任务ID
            copied_files: 已拷贝文件数
            status: 任务状态
            total_files: 总文件数（可选，用于更新总文件数）
        """
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id]['copied_files'] = copied_files
                self.tasks[task_id]['status'] = status
                self.tasks[task_id]['last_update'] = time.time()
                if total_files is not None:
                    self.tasks[task_id]['total_files'] = total_files
    
    def complete_task(self, task_id: str, success: bool = True):
        """
        完成任务
        
        Args:
            task_id: 任务ID
            success: 是否成功
        """
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id]['status'] = 'completed' if success else 'failed'
                self.tasks[task_id]['last_update'] = time.time()
                # 不要强制设置进度为100%，保持实际的文件计数
                # 只有在实际拷贝完成时才更新文件计数
                if not success:
                    # 失败的任务保持当前进度
                    pass
                # 成功的任务保持当前的实际文件计数，不强制设置为100%
    
    def force_final_display(self):
        """强制显示最终状态"""
        with self.lock:
            # 检查是否所有任务都完成
            all_completed = all(
                task['status'] in ['completed', 'failed'] 
                for task in self.tasks.values()
            )
            
            # 总是显示进度条，让用户看到100%的进度
            self._display_progress()
            
            if all_completed and self.tasks:
                return True
            else:
                return False
    
    def _display_loop(self):
        """显示循环 - 每1秒更新一次"""
        while self.running:
            current_time = time.time()
            
            # 检查是否所有任务都完成
            with self.lock:
                all_completed = all(
                    task['status'] in ['completed', 'failed'] 
                    for task in self.tasks.values()
                )
            
            if all_completed and self.tasks:
                # 显示100%的进度条，让用户看到完成状态
                self._display_progress()
                time.sleep(1)  # 只等待1秒
                self._display_final_summary()
                self.running = False  # 停止显示循环
                break  # 立即退出循环，避免重复显示
            
            # 检查是否需要更新显示
            if current_time - self.last_update >= self.refresh_interval:
                # 检查是否有任务状态变化，避免无意义的刷新
                has_changes = False
                with self.lock:
                    for task in self.tasks.values():
                        if task['status'] == 'running' and current_time - task['last_update'] < 180:  # 最近3分钟有更新
                            has_changes = True
                            break
                        elif task['status'] in ['completed', 'failed'] and current_time - task['last_update'] < 60:  # 最近1分钟状态变化
                            has_changes = True
                            break
                
                # 第一次显示或者有变化时显示
                if has_changes or not hasattr(self, '_last_display_time') or self.display_count == 0:
                    self._display_progress()
                    self._last_display_time = current_time
                self.last_update = current_time
            
            # 检查是否有任务超时（超过10分钟没有更新）
            current_time = time.time()
            with self.lock:
                for task_id, task in self.tasks.items():
                    if task['status'] == 'running' and current_time - task['last_update'] > 600:  # 10分钟超时
                        logger.warning(f"Task {task_id} has been running for more than 10 minutes, marking as failed")
                        task['status'] = 'failed'
                        task['last_update'] = current_time
            
            time.sleep(1)  # 每秒检查一次
    
    def _display_progress(self):
        """显示当前进度 - 超简洁版本"""
        with self.lock:
            if not self.tasks or self.is_displaying:
                return
            
            self.is_displaying = True
            
            try:
                # 清屏并显示进度
                os.system('cls' if os.name == 'nt' else 'clear')
                
                # 计算总体进度
                total_tasks = len(self.tasks)
                completed_tasks = sum(1 for task in self.tasks.values() if task['status'] == 'completed')
                failed_tasks = sum(1 for task in self.tasks.values() if task['status'] == 'failed')
                running_tasks = total_tasks - completed_tasks - failed_tasks
                
                # 当所有任务都完成或失败时，显示100%进度
                if completed_tasks + failed_tasks == total_tasks and total_tasks > 0:
                    overall_progress = 100.0
                else:
                    overall_progress = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
                
                # 显示超简洁的总体信息
                elapsed_time = self._format_time(time.time() - self.start_time)
                print(f"Progress: {completed_tasks}/{total_tasks} ({overall_progress:.1f}%) | Time: {elapsed_time}")
                print()
                
                # 显示每个任务的进度
                for task_id, task in self.tasks.items():
                    self._display_task_progress(task_id, task)
                
                print()
                if running_tasks > 0:
                    print("Tasks in progress...")
                else:
                    print("All tasks completed!")
                    
            finally:
                self.is_displaying = False
    
    def _display_task_progress(self, task_id: str, task: Dict[str, Any]):
        """显示单个任务的进度 - 最简洁版本"""
        total_files = task['total_files']
        copied_files = task['copied_files']
        status = task['status']
        
        # 计算进度百分比，确保不超过100%
        if total_files > 0:
            progress = min((copied_files / total_files) * 100, 100.0)
        else:
            progress = 0
        
        # 状态图标
        status_icon = {
            'running': 'PROCESSING:',
            'completed': 'SUCCESS:',
            'failed': 'ERROR:'
        }.get(status, '[UNKNOWN]')
        
        # 创建简洁的进度条
        bar_length = 15
        filled_length = int(bar_length * progress / 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        # 最简洁的显示格式
        print(f"{status_icon} {task_id:<25} [{bar}] {progress:5.1f}%")
    
    def _display_final_summary(self):
        """显示最终总结"""
        with self.lock:
            # 清屏
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print("=" * 80)
            print("Data Copy - Final Summary")
            print("=" * 80)
            
            total_tasks = len(self.tasks)
            completed_tasks = sum(1 for task in self.tasks.values() if task['status'] == 'completed')
            failed_tasks = sum(1 for task in self.tasks.values() if task['status'] == 'failed')
            
            print(f"Total Tasks: {total_tasks}")
            print(f"Completed: {completed_tasks}")
            print(f"Failed: {failed_tasks}")
            print(f"Total Time: {self._format_time(time.time() - self.start_time)}")
            print("=" * 80)
            
            # 显示每个任务的最终状态
            for task_id, task in self.tasks.items():
                status_icon = 'SUCCESS:' if task['status'] == 'completed' else 'ERROR:'
                print(f"{status_icon} {task_id}: {task['source']} → {task['target']}")
            
            print("=" * 80)
            
            # 停止显示循环，避免重复输出
            self.running = False
    
    def _format_time(self, seconds: float) -> str:
        """格式化时间显示"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    
    def stop(self):
        """停止进度跟踪器"""
        self.running = False
        if self.display_thread.is_alive():
            self.display_thread.join(timeout=2)

# 全局进度跟踪器实例
_global_tracker = None

def get_progress_tracker(refresh_interval: int = 30) -> DetailedProgressTracker:
    """获取全局进度跟踪器实例"""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = DetailedProgressTracker(refresh_interval)
    return _global_tracker

def stop_progress_tracker():
    """停止全局进度跟踪器"""
    global _global_tracker
    if _global_tracker:
        _global_tracker.stop()
        _global_tracker = None
