"""
下载状态检测器
提供准确的下载状态识别和管理功能
支持三种主要状态：下载中、下载失败、下载完成
"""

import asyncio
import json
import os
import platform
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Set
from playwright.async_api import Page
import aiofiles
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class DownloadStatus(Enum):
    """下载状态枚举"""
    PENDING = "pending"        # 等待下载
    DOWNLOADING = "downloading"  # 下载中
    COMPLETED = "completed"    # 下载完成
    FAILED = "failed"         # 下载失败
    CANCELLED = "cancelled"    # 下载取消
    TIMEOUT = "timeout"       # 下载超时


@dataclass
class DownloadTask:
    """下载任务数据结构"""
    task_id: str                    # 唯一标识符
    file_name: str                  # 文件名
    file_url: str                   # 文件URL
    status: DownloadStatus          # 下载状态
    progress: float = 0.0           # 下载进度 (0.0-1.0)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    save_path: Optional[str] = None
    file_size: Optional[int] = None
    expected_size: Optional[int] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    download_method: str = "browser_default"
    browser_type: str = "chromium"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data['status'] = self.status.value
        data['start_time'] = self.start_time.isoformat() if self.start_time else None
        data['end_time'] = self.end_time.isoformat() if self.end_time else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DownloadTask':
        """从字典创建实例"""
        data['status'] = DownloadStatus(data['status'])
        data['start_time'] = datetime.fromisoformat(data['start_time']) if data['start_time'] else None
        data['end_time'] = datetime.fromisoformat(data['end_time']) if data['end_time'] else None
        return cls(**data)


class FileSystemEventHandler(FileSystemEventHandler):
    """文件系统事件处理器"""
    
    def __init__(self, status_manager: 'DownloadStatusManager'):
        self.status_manager = status_manager
        self.temp_files: Set[str] = set()
    
    def on_created(self, event):
        """文件创建事件"""
        if not event.is_directory:
            self.status_manager._handle_file_created(event.src_path)
    
    def on_modified(self, event):
        """文件修改事件"""
        if not event.is_directory:
            self.status_manager._handle_file_modified(event.src_path)
    
    def on_moved(self, event):
        """文件移动事件"""
        if not event.is_directory:
            self.status_manager._handle_file_moved(event.src_path, event.dest_path)


class DownloadStatusManager:
    """下载状态管理器"""
    
    def __init__(self, state_file: str = "downloads/download_state.json"):
        self.tasks: Dict[str, DownloadTask] = {}
        self.status_callbacks: Dict[DownloadStatus, List[Callable]] = {}
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 文件系统监控
        self.file_observer = None
        self.file_handler = None
        self._setup_file_monitoring()
        
        # 超时配置
        self.timeout_config = {
            'start_timeout': 10,     # 启动超时
            'progress_timeout': 120, # 进度超时（增加到2分钟）
            'completion_timeout': 180 # 完成超时（增加到3分钟）
        }
        
        # 加载已保存的状态
        self._load_state()
    
    def _setup_file_monitoring(self):
        """设置文件系统监控"""
        try:
            self.file_handler = FileSystemEventHandler(self)
            self.file_observer = Observer()
            
            # 监控下载目录
            download_dirs = [
                Path.home() / "Downloads",
                Path("downloads"),
                Path.cwd() / "downloads"
            ]
            
            for download_dir in download_dirs:
                if download_dir.exists():
                    self.file_observer.schedule(
                        self.file_handler, 
                        str(download_dir), 
                        recursive=False
                    )
                    break
            
            self.file_observer.start()
        except Exception as e:
            print(f"⚠️ 文件系统监控设置失败: {e}")
    
    def create_task(self, file_info: Dict[str, Any]) -> DownloadTask:
        """创建新的下载任务"""
        task_id = f"task_{int(time.time() * 1000)}_{len(self.tasks)}"
        
        task = DownloadTask(
            task_id=task_id,
            file_name=file_info.get('name', 'unknown_file'),
            file_url=file_info.get('url', ''),
            status=DownloadStatus.PENDING,
            start_time=datetime.now(),
            download_method=file_info.get('method', 'browser_default'),
            browser_type=file_info.get('browser_type', 'chromium')
        )
        
        self.tasks[task_id] = task
        self._save_state()
        
        return task
    
    def update_status(self, task_id: str, status: DownloadStatus, *, suppress_log: bool = False, **kwargs):
        """更新任务状态"""
        if task_id not in self.tasks:
            return
        
        task = self.tasks[task_id]
        old_status = task.status
        task.status = status
        
        # 更新其他字段
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        # 设置时间戳
        if status == DownloadStatus.DOWNLOADING and not task.start_time:
            task.start_time = datetime.now()
        elif status in [DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELLED]:
            task.end_time = datetime.now()
        
        # 触发回调
        self._trigger_callbacks(task_id, old_status, status)
        
        # 保存状态
        self._save_state()
        
        if not suppress_log:
            print(f"📊 下载状态更新: {task.file_name} [{old_status.value} → {status.value}]")
    
    def get_task_status(self, task_id: str) -> Optional[DownloadStatus]:
        """获取任务状态"""
        task = self.tasks.get(task_id)
        return task.status if task else None
    
    def get_tasks_by_status(self, status: DownloadStatus) -> List[DownloadTask]:
        """按状态获取任务列表"""
        return [task for task in self.tasks.values() if task.status == status]
    
    def register_callback(self, status: DownloadStatus, callback: Callable):
        """注册状态变化回调"""
        if status not in self.status_callbacks:
            self.status_callbacks[status] = []
        self.status_callbacks[status].append(callback)
    
    def _trigger_callbacks(self, task_id: str, old_status: DownloadStatus, new_status: DownloadStatus):
        """触发状态变化回调"""
        if new_status in self.status_callbacks:
            for callback in self.status_callbacks[new_status]:
                try:
                    callback(task_id, self.tasks[task_id])
                except Exception as e:
                    print(f"⚠️ 回调执行失败: {e}")
    
    def _handle_file_created(self, file_path: str):
        """处理文件创建事件"""
        file_path = Path(file_path)
        
        # 查找匹配的下载任务
        for task in self.tasks.values():
            if (task.status == DownloadStatus.DOWNLOADING and 
                task.file_name in file_path.name):
                self._update_progress_from_file(task, file_path)
    
    def _handle_file_modified(self, file_path: str):
        """处理文件修改事件"""
        file_path = Path(file_path)
        
        # 查找匹配的下载任务
        for task in self.tasks.values():
            if (task.status == DownloadStatus.DOWNLOADING and 
                task.file_name in file_path.name):
                self._update_progress_from_file(task, file_path)
    
    def _handle_file_moved(self, src_path: str, dest_path: str):
        """处理文件移动事件"""
        dest_path = Path(dest_path)
        
        # 查找匹配的下载任务
        for task in self.tasks.values():
            if (task.status == DownloadStatus.DOWNLOADING and 
                task.file_name in dest_path.name):
                task.save_path = str(dest_path)
                self._update_progress_from_file(task, dest_path)
    
    def _update_progress_from_file(self, task: DownloadTask, file_path: Path):
        """从文件更新进度"""
        try:
            if file_path.exists():
                current_size = file_path.stat().st_size
                old_size = task.file_size or 0
                task.file_size = current_size
                
                # 计算进度
                if task.expected_size and task.expected_size > 0:
                    task.progress = min(current_size / task.expected_size, 1.0)
                else:
                    # 如果没有预期大小，基于文件大小变化估算
                    if current_size > 0:
                        # 基于文件大小估算进度（假设文件不会超过100MB）
                        task.progress = min(current_size / (100 * 1024 * 1024), 0.95)
                    else:
                        task.progress = 0.0
                
                # 显示进度更新
                if current_size > old_size:
                    size_diff = current_size - old_size
                    print(f"   📈 文件进度更新: {task.file_name} - {current_size:,} 字节 (+{size_diff:,})")
                
                # 检查是否完成
                if self._is_file_download_complete(file_path):
                    self.update_status(
                        task.task_id, 
                        DownloadStatus.COMPLETED,
                        save_path=str(file_path),
                        file_size=current_size,
                        progress=1.0
                    )
                    print(f"   ✅ 文件下载完成: {task.file_name} ({current_size:,} 字节)")
        except Exception as e:
            print(f"⚠️ 更新文件进度失败: {e}")
    
    def _is_file_download_complete(self, file_path: Path) -> bool:
        """检查文件下载是否完成"""
        try:
            if not file_path.exists():
                return False
            
            # 检查文件是否被锁定（Windows）
            if platform.system() == "Windows":
                try:
                    with open(file_path, 'r+b') as f:
                        pass
                except (PermissionError, OSError):
                    return False  # 文件被锁定，仍在下载
            
            # 检查文件大小是否稳定（更宽松的检测）
            size1 = file_path.stat().st_size
            time.sleep(0.5)  # 等待更长时间
            size2 = file_path.stat().st_size
            
            # 如果文件大小稳定且大于0，认为下载完成
            if size1 == size2 and size1 > 0:
                # 再检查一次，确保真的稳定
                time.sleep(0.5)
                size3 = file_path.stat().st_size
                return size2 == size3
            
            return False
            
        except Exception:
            return False
    
    def _save_state(self):
        """保存状态到文件"""
        try:
            state_data = {
                'tasks': {task_id: task.to_dict() for task_id, task in self.tasks.items()},
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"⚠️ 保存状态失败: {e}")
    
    def _load_state(self):
        """从文件加载状态"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                
                for task_id, task_data in state_data.get('tasks', {}).items():
                    try:
                        task = DownloadTask.from_dict(task_data)
                        self.tasks[task_id] = task
                    except Exception as e:
                        print(f"⚠️ 加载任务失败 {task_id}: {e}")
                        
        except Exception as e:
            print(f"⚠️ 加载状态失败: {e}")
    
    def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """清理已完成的任务"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        tasks_to_remove = []
        for task_id, task in self.tasks.items():
            if (task.status in [DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELLED] and
                task.end_time and task.end_time < cutoff_time):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
        
        if tasks_to_remove:
            self._save_state()
            print(f"🧹 清理了 {len(tasks_to_remove)} 个过期任务")
    
    def get_summary(self) -> Dict[str, Any]:
        """获取下载摘要"""
        total_tasks = len(self.tasks)
        status_counts = {}
        
        for status in DownloadStatus:
            status_counts[status.value] = len(self.get_tasks_by_status(status))
        
        return {
            'total_tasks': total_tasks,
            'status_counts': status_counts,
            'active_downloads': len(self.get_tasks_by_status(DownloadStatus.DOWNLOADING)),
            'completed_downloads': len(self.get_tasks_by_status(DownloadStatus.COMPLETED)),
            'failed_downloads': len(self.get_tasks_by_status(DownloadStatus.FAILED)),
            'success_rate': (
                status_counts.get('completed', 0) / total_tasks * 100 
                if total_tasks > 0 else 0
            )
        }
    
    def close(self):
        """关闭状态管理器"""
        if self.file_observer:
            self.file_observer.stop()
            self.file_observer.join()


class DownloadStatusDetector:
    """下载状态检测器"""
    
    def __init__(self, status_manager: DownloadStatusManager):
        self.status_manager = status_manager
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
    
    async def start_monitoring(self, task_id: str, page: Page, download_path: Path):
        """开始监控下载状态"""
        if task_id in self.monitoring_tasks:
            return
        
        # 创建监控任务
        monitor_task = asyncio.create_task(
            self._monitor_download_status(task_id, page, download_path)
        )
        self.monitoring_tasks[task_id] = monitor_task
    
    async def stop_monitoring(self, task_id: str):
        """停止监控下载状态"""
        if task_id in self.monitoring_tasks:
            self.monitoring_tasks[task_id].cancel()
            del self.monitoring_tasks[task_id]
    
    async def _monitor_download_status(self, task_id: str, page: Page, download_path: Path):
        """监控下载状态的主循环"""
        task = self.status_manager.tasks.get(task_id)
        if not task:
            return
        
        try:
            # 阶段1: 等待下载启动
            await self._wait_for_download_start(task_id, page)
            
            # 阶段2: 监控下载进度
            await self._monitor_download_progress(task_id, download_path)
            
            # 阶段3: 检测下载完成
            await self._detect_download_completion(task_id, download_path)
            
        except asyncio.CancelledError:
            self.status_manager.update_status(task_id, DownloadStatus.CANCELLED)
        except Exception as e:
            self.status_manager.update_status(
                task_id, 
                DownloadStatus.FAILED,
                error_message=str(e)
            )
        finally:
            await self.stop_monitoring(task_id)
    
    async def _wait_for_download_start(self, task_id: str, page: Page):
        """等待下载启动"""
        timeout = self.status_manager.timeout_config['start_timeout']
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # 检查网络请求状态
            if await self._check_network_activity(page):
                self.status_manager.update_status(task_id, DownloadStatus.DOWNLOADING)
                return
            
            await asyncio.sleep(0.1)
        
        # 超时
        self.status_manager.update_status(
            task_id, 
            DownloadStatus.TIMEOUT,
            error_message="下载启动超时"
        )
        raise TimeoutError("下载启动超时")
    
    async def _monitor_download_progress(self, task_id: str, download_path: Path):
        """监控下载进度"""
        timeout = self.status_manager.timeout_config['progress_timeout']
        start_time = time.time()
        last_size = 0
        last_time = start_time
        no_progress_count = 0
        progress_check_interval = 1.0  # 每秒检查一次进度
        stable_size_count = 0  # 文件大小稳定的次数
        
        print(f"📊 开始监控下载进度: {task_id}")
        
        while time.time() - start_time < timeout:
            task = self.status_manager.tasks.get(task_id)
            if not task:
                print(f"   📊 监控结束: 任务不存在")
                break
            elif task.status != DownloadStatus.DOWNLOADING:
                print(f"   📊 监控结束: 任务状态已改变为 {task.status.value}")
                break
            
            current_time = time.time()
            # 检查文件大小变化
            current_size = await self._get_current_file_size(task, download_path)
            
            if current_size > last_size:
                # 有进度，计算下载速度
                no_progress_count = 0
                stable_size_count = 0
                size_diff = current_size - last_size
                time_diff = current_time - last_time
                
                if time_diff > 0:
                    download_speed = size_diff / time_diff  # 字节/秒
                    speed_mb_s = download_speed / (1024 * 1024)  # MB/秒
                    
                    # 更新进度和速度信息
                    if task.expected_size and task.expected_size > 0:
                        progress = min(current_size / task.expected_size, 1.0)
                    else:
                        # 如果没有预期大小，基于时间估算进度
                        elapsed_time = current_time - start_time
                        progress = min(elapsed_time / 60, 0.95)  # 假设最多1分钟
                    
                    self.status_manager.update_status(
                        task_id, 
                        DownloadStatus.DOWNLOADING,
                        file_size=current_size,
                        progress=progress
                    )
                    
                    # 显示下载进度
                    print(f"   📈 下载进度: {progress*100:.1f}% ({current_size:,} 字节) - 速度: {speed_mb_s:.2f} MB/s")
                
                last_size = current_size
                last_time = current_time
            elif current_size == last_size and current_size > 0:
                # 文件大小稳定，可能是下载完成
                stable_size_count += 1
                no_progress_count += 1
                
                if stable_size_count >= 5:  # 连续5次检查文件大小都稳定
                    print(f"   ✅ 文件大小稳定，可能下载完成: {current_size:,} 字节")
                    # 检查文件是否真的完成
                    if await self._is_download_complete(task, download_path):
                        self.status_manager.update_status(
                            task_id, 
                            DownloadStatus.COMPLETED,
                            save_path=str(download_path / task.file_name),
                            file_size=current_size,
                            progress=1.0
                        )
                        print(f"   ✅ 下载完成: {task.file_name} ({current_size:,} 字节)")
                        return
                
                if no_progress_count > 30:  # 连续30秒无进度才认为停滞
                    print(f"   ⚠️ 下载进度停滞 {no_progress_count} 秒")
                    if no_progress_count > 60:  # 连续60秒无进度才失败
                        self.status_manager.update_status(
                            task_id, 
                            DownloadStatus.FAILED,
                            error_message="下载进度停滞超过60秒"
                        )
                        return
            else:
                # 无进度且文件大小为0
                no_progress_count += 1
                if no_progress_count > 30:  # 连续30秒无进度才认为停滞
                    print(f"   ⚠️ 下载进度停滞 {no_progress_count} 秒")
                    if no_progress_count > 60:  # 连续60秒无进度才失败
                        self.status_manager.update_status(
                            task_id, 
                            DownloadStatus.FAILED,
                            error_message="下载进度停滞超过60秒"
                        )
                        return
            
            await asyncio.sleep(progress_check_interval)
        
        # 进度监控超时
        print(f"   ⏰ 下载进度监控超时 ({timeout} 秒)")
        # 检查最终状态，如果文件存在且大小稳定，标记为完成
        task = self.status_manager.tasks.get(task_id)
        if task:
            final_size = await self._get_current_file_size(task, download_path)
            if final_size > 0 and await self._is_download_complete(task, download_path):
                self.status_manager.update_status(
                    task_id, 
                    DownloadStatus.COMPLETED,
                    save_path=str(download_path / task.file_name),
                    file_size=final_size,
                    progress=1.0
                )
                print(f"   ✅ 最终检查：下载完成: {task.file_name} ({final_size:,} 字节)")
            else:
                self.status_manager.update_status(
                    task_id, 
                    DownloadStatus.TIMEOUT,
                    error_message=f"下载进度监控超时 ({timeout} 秒)"
                )
    
    async def _detect_download_completion(self, task_id: str, download_path: Path):
        """检测下载完成"""
        timeout = self.status_manager.timeout_config['completion_timeout']
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            task = self.status_manager.tasks.get(task_id)
            if not task:
                break
            
            # 检查文件是否完成
            if await self._is_download_complete(task, download_path):
                self.status_manager.update_status(
                    task_id, 
                    DownloadStatus.COMPLETED,
                    save_path=str(download_path / task.file_name),
                    file_size=task.file_size
                )
                return
            
            await asyncio.sleep(0.5)
        
        # 完成检测超时
        self.status_manager.update_status(
            task_id, 
            DownloadStatus.TIMEOUT,
            error_message="下载完成检测超时"
        )
    
    async def _check_network_activity(self, page: Page) -> bool:
        """检查网络活动"""
        try:
            # 这里可以添加更复杂的网络活动检测逻辑
            # 目前返回True表示有活动
            return True
        except Exception:
            return False
    
    async def _get_current_file_size(self, task: DownloadTask, download_path: Path) -> int:
        """获取当前文件大小"""
        try:
            file_path = download_path / task.file_name
            if file_path.exists():
                return file_path.stat().st_size
        except Exception:
            pass
        return 0
    
    async def _is_download_complete(self, task: DownloadTask, download_path: Path) -> bool:
        """检查下载是否完成"""
        try:
            file_path = download_path / task.file_name
            if not file_path.exists():
                return False
            
            # 检查文件大小是否稳定
            size1 = file_path.stat().st_size
            await asyncio.sleep(0.1)
            size2 = file_path.stat().st_size
            
            return size1 == size2 and size1 > 0
            
        except Exception:
            return False


# 便捷函数
def create_download_status_manager(state_file: str = "downloads/download_state.json") -> DownloadStatusManager:
    """创建下载状态管理器"""
    return DownloadStatusManager(state_file)


def create_download_status_detector(status_manager: DownloadStatusManager) -> DownloadStatusDetector:
    """创建下载状态检测器"""
    return DownloadStatusDetector(status_manager)


# 状态回调示例
def on_download_completed(task_id: str, task: DownloadTask):
    """下载完成回调示例"""
    print(f"🎉 下载完成: {task.file_name} ({task.file_size} 字节)")


def on_download_failed(task_id: str, task: DownloadTask):
    """下载失败回调示例"""
    print(f"❌ 下载失败: {task.file_name} - {task.error_message}")


def on_download_started(task_id: str, task: DownloadTask):
    """下载开始回调示例"""
    print(f"🚀 开始下载: {task.file_name}")


if __name__ == "__main__":
    # 测试代码
    async def test_download_status_manager():
        """测试下载状态管理器"""
        manager = create_download_status_manager()
        
        # 注册回调
        manager.register_callback(DownloadStatus.COMPLETED, on_download_completed)
        manager.register_callback(DownloadStatus.FAILED, on_download_failed)
        manager.register_callback(DownloadStatus.DOWNLOADING, on_download_started)
        
        # 创建测试任务
        file_info = {
            'name': 'test_file.pdf',
            'url': 'https://example.com/test_file.pdf',
            'method': 'browser_default'
        }
        
        task = manager.create_task(file_info)
        print(f"创建任务: {task.task_id}")
        
        # 模拟状态变化
        manager.update_status(task.task_id, DownloadStatus.DOWNLOADING)
        await asyncio.sleep(1)
        
        manager.update_status(task.task_id, DownloadStatus.COMPLETED, file_size=1024)
        
        # 显示摘要
        summary = manager.get_summary()
        print(f"下载摘要: {summary}")
        
        manager.close()
    
    # 运行测试
    asyncio.run(test_download_status_manager())
