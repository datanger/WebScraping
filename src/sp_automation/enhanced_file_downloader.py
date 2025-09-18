"""
增强版文件下载器
集成下载状态检测功能，提供准确的下载状态管理
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from playwright.async_api import Page

from .file_downloader import SharePointFileDownloader
from .download_status_detector import (
    DownloadStatusManager, 
    DownloadStatusDetector,
    DownloadStatus,
    create_download_status_manager,
    create_download_status_detector
)
from .safe_operations import SharePointSafetyManager
from .config import settings


class EnhancedSharePointFileDownloader(SharePointFileDownloader):
    """增强版 SharePoint 文件下载器，集成状态检测功能"""
    
    def __init__(self, safety_manager: SharePointSafetyManager, state_file: str = "downloads/download_state.json"):
        super().__init__(safety_manager)
        
        # 初始化状态管理器
        self.status_manager = create_download_status_manager(state_file)
        self.status_detector = create_download_status_detector(self.status_manager)
        
        # 注册状态回调
        self._register_status_callbacks()
    
    def _register_status_callbacks(self):
        """注册状态变化回调"""
        self.status_manager.register_callback(DownloadStatus.DOWNLOADING, self._on_download_started)
        self.status_manager.register_callback(DownloadStatus.COMPLETED, self._on_download_completed)
        self.status_manager.register_callback(DownloadStatus.FAILED, self._on_download_failed)
        self.status_manager.register_callback(DownloadStatus.TIMEOUT, self._on_download_timeout)
    
    async def download_file_with_status_tracking(self, page: Page, file_info: Dict[str, Any]) -> str:
        """带状态跟踪的文件下载"""
        # 1. 创建下载任务
        task = self.status_manager.create_task(file_info)
        print(f"🚀 创建下载任务: {task.file_name} (ID: {task.task_id})")
        
        try:
            # 2. 开始状态监控
            download_path = Path(settings.download_path) if settings.download_path else Path.home() / "Downloads"
            await self.status_detector.start_monitoring(task.task_id, page, download_path)
            
            # 3. 执行下载
            success = await self.download_file_by_right_click(page, file_info)
            
            # 4. 等待状态检测完成，但检查状态变化
            max_wait_time = 10  # 最多等待10秒
            wait_interval = 0.5  # 每0.5秒检查一次
            waited_time = 0
            
            while waited_time < max_wait_time:
                final_status = self.status_manager.get_task_status(task.task_id)
                if final_status != DownloadStatus.DOWNLOADING:
                    print(f"   📊 状态检测器已更新状态为: {final_status.value}")
                    break
                await asyncio.sleep(wait_interval)
                waited_time += wait_interval
            
            # 5. 如果状态检测器没有更新状态，手动更新
            final_status = self.status_manager.get_task_status(task.task_id)
            if final_status == DownloadStatus.DOWNLOADING:
                print(f"   ⚠️ 状态检测器未更新状态，手动检查...")
                if success:
                    # 检查文件是否真的存在
                    file_path = download_path / task.file_name
                    if file_path.exists():
                        file_size = file_path.stat().st_size
                        self.status_manager.update_status(
                            task.task_id, 
                            DownloadStatus.COMPLETED,
                            save_path=str(file_path),
                            file_size=file_size,
                            progress=1.0
                        )
                        print(f"   ✅ 手动更新：下载完成: {task.file_name} ({file_size:,} 字节)")
                    else:
                        self.status_manager.update_status(
                            task.task_id, 
                            DownloadStatus.FAILED,
                            error_message="文件下载后未找到"
                        )
                else:
                    self.status_manager.update_status(
                        task.task_id, 
                        DownloadStatus.FAILED,
                        error_message="下载执行失败"
                    )
            
            return task.task_id
            
        except Exception as e:
            # 异常处理
            self.status_manager.update_status(
                task.task_id, 
                DownloadStatus.FAILED,
                error_message=str(e)
            )
            raise
        finally:
            # 停止监控
            await self.status_detector.stop_monitoring(task.task_id)
    
    async def download_files_with_status_tracking(self, page: Page, file_list: List[Dict[str, Any]]) -> List[str]:
        """批量下载文件（带状态跟踪）"""
        task_ids = []
        
        print(f"📥 开始批量下载 {len(file_list)} 个文件...")
        
        for i, file_info in enumerate(file_list, 1):
            print(f"\n📁 下载文件 {i}/{len(file_list)}: {file_info.get('name', 'unknown')}")
            
            try:
                task_id = await self.download_file_with_status_tracking(page, file_info)
                task_ids.append(task_id)
                
                # 显示当前进度
                self._show_download_progress()
                
            except Exception as e:
                print(f"❌ 下载失败: {file_info.get('name', 'unknown')} - {e}")
                continue
        
        # 显示最终摘要
        self._show_final_summary()
        
        return task_ids
    
    def _show_download_progress(self):
        """显示下载进度"""
        summary = self.status_manager.get_summary()
        
        print(f"📊 当前进度:")
        print(f"   • 总任务: {summary['total_tasks']}")
        print(f"   • 下载中: {summary['active_downloads']}")
        print(f"   • 已完成: {summary['completed_downloads']}")
        print(f"   • 失败: {summary['failed_downloads']}")
        print(f"   • 成功率: {summary['success_rate']:.1f}%")
    
    def _show_final_summary(self):
        """显示最终摘要"""
        summary = self.status_manager.get_summary()
        
        print(f"\n🎯 下载完成摘要:")
        print(f"   • 总任务数: {summary['total_tasks']}")
        print(f"   • 成功下载: {summary['completed_downloads']}")
        print(f"   • 下载失败: {summary['failed_downloads']}")
        print(f"   • 成功率: {summary['success_rate']:.1f}%")
        
        # 显示详细状态
        for status in [DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.TIMEOUT]:
            tasks = self.status_manager.get_tasks_by_status(status)
            if tasks:
                print(f"\n📋 {status.value.upper()} 文件:")
                for task in tasks:
                    if status == DownloadStatus.COMPLETED:
                        print(f"   ✅ {task.file_name} ({task.file_size} 字节)")
                    else:
                        print(f"   ❌ {task.file_name} - {task.error_message}")
    
    def get_download_tasks_by_status(self, status: DownloadStatus) -> List[Dict[str, Any]]:
        """获取指定状态的任务列表"""
        tasks = self.status_manager.get_tasks_by_status(status)
        return [task.to_dict() for task in tasks]
    
    def get_download_summary(self) -> Dict[str, Any]:
        """获取下载摘要（增强版）"""
        base_summary = super().get_download_summary()
        status_summary = self.status_manager.get_summary()
        
        # 合并摘要信息
        enhanced_summary = {
            **base_summary,
            **status_summary,
            'status_details': {
                status.value: len(self.status_manager.get_tasks_by_status(status))
                for status in DownloadStatus
            }
        }
        
        return enhanced_summary
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理过期任务"""
        self.status_manager.cleanup_completed_tasks(max_age_hours)
    
    def close(self):
        """关闭下载器"""
        self.status_manager.close()
    
    # 状态回调方法
    def _on_download_started(self, task_id: str, task):
        """下载开始回调"""
        print(f"🚀 开始下载: {task.file_name}")
    
    def _on_download_completed(self, task_id: str, task):
        """下载完成回调"""
        print(f"✅ 下载完成: {task.file_name} ({task.file_size} 字节)")
    
    def _on_download_failed(self, task_id: str, task):
        """下载失败回调"""
        print(f"❌ 下载失败: {task.file_name} - {task.error_message}")
    
    def _on_download_timeout(self, task_id: str, task):
        """下载超时回调"""
        print(f"⏰ 下载超时: {task.file_name} - {task.error_message}")


# 便捷函数
def create_enhanced_downloader(
    safety_manager: SharePointSafetyManager, 
    state_file: str = "downloads/download_state.json"
) -> EnhancedSharePointFileDownloader:
    """创建增强版下载器"""
    return EnhancedSharePointFileDownloader(safety_manager, state_file)


# 使用示例
async def example_usage():
    """使用示例"""
    from .safe_operations import SharePointSafetyManager
    
    # 创建安全管理器
    safety_manager = SharePointSafetyManager(
        allowed_download_path="downloads",
        allowed_sharepoint_path="Test",
        test_mode=True
    )
    
    # 创建增强版下载器
    downloader = create_enhanced_downloader(safety_manager)
    
    try:
        # 模拟文件信息
        file_info = {
            'name': 'example_file.pdf',
            'url': 'https://sharepoint.com/example_file.pdf',
            'method': 'browser_default'
        }
        
        # 这里需要实际的 page 对象
        # task_id = await downloader.download_file_with_status_tracking(page, file_info)
        
        # 获取摘要
        summary = downloader.get_download_summary()
        print(f"下载摘要: {summary}")
        
    finally:
        downloader.close()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())
