"""
CDP 浏览器原生下载器监控组件

功能:
- 通过 Chromium/Edge 的 DevTools 协议监听浏览器原生下载事件
- 事件: Page.downloadWillBegin / Page.downloadProgress
- 将进度(字节/百分比/速度)与状态(进行中/完成/取消)同步到 DownloadStatusManager

使用示例:
    monitor = BrowserDownloadMonitor(status_manager)
    cdp = await monitor.attach_to_page(page)
    # 触发下载...
    await monitor.detach()

限制:
- 仅支持 Chromium/Edge (Firefox 无该下载事件)
"""

from __future__ import annotations

import time
from typing import Dict, Optional

from playwright.async_api import Page

from .download_status_detector import (
    DownloadStatus,
    DownloadStatusManager,
)


class BrowserDownloadMonitor:
    """基于 CDP 的浏览器原生下载监控器。"""

    def __init__(self, status_manager: DownloadStatusManager) -> None:
        self.status_manager = status_manager
        self._guid_to_task: Dict[str, str] = {}
        self._last_bytes: Dict[str, int] = {}
        self._last_time: Dict[str, float] = {}
        self._cdp = None

    async def attach_to_page(self, page: Page):
        """附加到指定 Page，开始监听下载事件。"""
        context = page.context
        self._cdp = await context.new_cdp_session(page)
        await self._cdp.send("Page.enable")

        async def on_download_begin(params):
            guid = params.get("guid")
            url = params.get("url")
            suggested = params.get("suggestedFilename") or "downloaded_file"

            file_info = {"name": suggested, "url": url, "method": "cdp"}
            task = self.status_manager.create_task(file_info)
            self._guid_to_task[guid] = task.task_id
            self._last_bytes[guid] = 0
            self._last_time[guid] = time.time()
            self.status_manager.update_status(task.task_id, DownloadStatus.DOWNLOADING, file_size=0, progress=0.0)

        async def on_download_progress(params):
            guid = params.get("guid")
            state = params.get("state")  # inProgress / completed / canceled
            total = params.get("totalBytes")
            recv = params.get("receivedBytes", 0)
            task_id = self._guid_to_task.get(guid)
            if not task_id:
                return

            now = time.time()
            last_b = self._last_bytes.get(guid, 0)
            last_t = self._last_time.get(guid, now)
            speed = (recv - last_b) / (now - last_t) if now > last_t else 0.0  # bytes/s
            self._last_bytes[guid] = recv
            self._last_time[guid] = now

            progress = min(recv / total, 1.0) if total else 0.0

            if state == "inProgress":
                self.status_manager.update_status(
                    task_id,
                    DownloadStatus.DOWNLOADING,
                    file_size=recv,
                    progress=progress,
                    suppress_log=True,
                )
                # 单行刷新输出，显示速度/百分比（避免冗余刷屏）
                try:
                    import sys as _sys
                    mb = recv / (1024 * 1024)
                    if total:
                        tot = total / (1024 * 1024)
                        pct = progress * 100
                        line = f"\r📥 {mb:.2f}MB / {tot:.2f}MB  {pct:5.1f}%  {speed/1024/1024:.2f} MB/s"
                    else:
                        line = f"\r📥 {mb:.2f}MB  ??.%  {speed/1024/1024:.2f} MB/s"
                    _sys.stdout.write(line)
                    _sys.stdout.flush()
                except Exception:
                    pass
            elif state == "completed":
                self.status_manager.update_status(
                    task_id,
                    DownloadStatus.COMPLETED,
                    file_size=recv,
                    progress=1.0,
                    suppress_log=True,
                )
                # 完成时换行并打印一次总结
                try:
                    import sys as _sys
                    _sys.stdout.write("\n")
                    _sys.stdout.flush()
                except Exception:
                    pass
                self._cleanup_guid(guid)
            elif state == "canceled":
                self.status_manager.update_status(
                    task_id,
                    DownloadStatus.CANCELLED,
                    error_message="浏览器取消下载",
                )
                self._cleanup_guid(guid)

        self._cdp.on("Page.downloadWillBegin", on_download_begin)
        self._cdp.on("Page.downloadProgress", on_download_progress)
        return self._cdp

    async def detach(self):
        """停止监听，释放 CDP 会话。"""
        if self._cdp:
            # Page.disable 非必需，这里仅释放句柄
            self._cdp = None

    def _cleanup_guid(self, guid: str):
        self._guid_to_task.pop(guid, None)
        self._last_bytes.pop(guid, None)
        self._last_time.pop(guid, None)


__all__ = ["BrowserDownloadMonitor"]


