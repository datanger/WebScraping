#!/usr/bin/env python3
"""
SharePoint 扫描 + CDP 下载监控（使用浏览器原生下载器状态）
- 复用现有扫描流程（连接 9222 上的浏览器）
- 在页面上触发的下载由 CDP 事件实时监控：百分比/速度/完成/取消
- 与 DownloadStatusManager 打通，支持 status/cleanup

用法：
  python scripts/scan_with_cdp_download_monitor.py scan      # 执行扫描并可选择下载（下载状态用浏览器下载器）
  python scripts/scan_with_cdp_download_monitor.py test      # 仅测试选择一个元素进行下载并监控
  python scripts/scan_with_cdp_download_monitor.py status    # 查看下载摘要
  python scripts/scan_with_cdp_download_monitor.py cleanup   # 清理过期任务
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.append('.')
from playwright.async_api import async_playwright
from src.sp_automation.sharepoint_scanner import SharePointScanner
from src.sp_automation.recursive_scanner import SharePointRecursiveScanner
from src.sp_automation.page_operations import navigate_to_url, check_login_required, get_page_info
from src.sp_automation.download_status_detector import (
    create_download_status_manager,
    DownloadStatus,
)

STATE_FILE = "downloads/download_state.json"
DEBUG_PORT = 9222

class ScanWithCdpDownloadMonitor:
    def __init__(self, debug_port: int = DEBUG_PORT, state_file: str = STATE_FILE):
        self.debug_port = debug_port
        self.state_file = state_file
        self.status_manager = create_download_status_manager(state_file)
        self.guid_to_task = {}
        self.last_bytes = {}
        self.last_time = {}

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.scanner = SharePointScanner(test_mode=True, debug_port=self.debug_port)
        ok = await self.scanner.connect_to_browser(self.playwright)
        if not ok:
            raise RuntimeError("无法连接到现有浏览器 (9222)")
        self.recursive = SharePointRecursiveScanner(self.scanner)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.scanner.cleanup_pages()
        await self.scanner.disconnect()
        self.status_manager.close()
        await self.playwright.stop()

    async def _attach_cdp_to_page(self, page):
        context = self.scanner.context
        cdp = await context.new_cdp_session(page)
        await cdp.send("Page.enable")

        async def on_download_begin(params):
            guid = params.get('guid')
            url = params.get('url')
            suggested = params.get('suggestedFilename') or "downloaded_file"
            print(f"🚀 [CDP] 下载开始: {suggested}")
            file_info = {"name": suggested, "url": url, "method": "cdp"}
            task = self.status_manager.create_task(file_info)
            self.guid_to_task[guid] = task.task_id
            self.last_bytes[guid] = 0
            self.last_time[guid] = time.time()
            self.status_manager.update_status(task.task_id, DownloadStatus.DOWNLOADING, file_size=0, progress=0.0)

        async def on_download_progress(params):
            guid = params.get('guid')
            state = params.get('state')
            total = params.get('totalBytes')
            recv = params.get('receivedBytes', 0)
            task_id = self.guid_to_task.get(guid)
            if not task_id:
                return

            now = time.time()
            last_b = self.last_bytes.get(guid, 0)
            last_t = self.last_time.get(guid, now)
            speed = (recv - last_b) / (now - last_t) if now > last_t else 0.0
            self.last_bytes[guid] = recv
            self.last_time[guid] = now

            progress = min(recv / total, 1.0) if total else 0.0

            if state == 'inProgress':
                self.status_manager.update_status(
                    task_id, DownloadStatus.DOWNLOADING,
                    file_size=recv, progress=progress
                )
                if total:
                    print(f"   📈 {recv/1024/1024:.2f}MB / {total/1024/1024:.2f}MB ({progress*100:.1f}%) - {speed/1024/1024:.2f} MB/s")
                else:
                    print(f"   📈 {recv/1024/1024:.2f}MB (未知总大小) - {speed/1024/1024:.2f} MB/s")
            elif state == 'completed':
                self.status_manager.update_status(task_id, DownloadStatus.COMPLETED, file_size=recv, progress=1.0)
                print(f"✅ [CDP] 下载完成 ({recv/1024/1024:.2f}MB)")
                self._cleanup_guid(guid)
            elif state == 'canceled':
                self.status_manager.update_status(task_id, DownloadStatus.CANCELLED, error_message="浏览器取消下载")
                print("⏹️ [CDP] 下载被取消")
                self._cleanup_guid(guid)

        cdp.on("Page.downloadWillBegin", on_download_begin)
        cdp.on("Page.downloadProgress", on_download_progress)
        return cdp

    def _cleanup_guid(self, guid: str):
        self.guid_to_task.pop(guid, None)
        self.last_bytes.pop(guid, None)
        self.last_time.pop(guid, None)

    async def scan_then_optionally_download(self, url: str):
        print("🚀 SharePoint 文件结构扫描器 (使用现有浏览器)")
        print("=" * 60)
        print("🔒 安全提醒：本脚本严格遵循 SharePoint 安全操作指南")
        print("   ✅ 只允许查看、预览、下载等只读操作")
        print("   ❌ 严格禁止删除、移动、重命名等危险操作")
        print("   🛡️ 测试模式下所有操作都需要用户确认")
        print("   📊 下载状态：由浏览器下载器 (CDP) 实时监控")
        print("=" * 60)
        print("🔍 开始扫描 SharePoint 文件结构")
        page = await self._open_page(url)
        await self._attach_cdp_to_page(page)

        # 递归扫描
        await self.recursive.recursive_scan_folders(page, url, current_path="")
        print(f"✅ 扫描完成，发现 {len(self.scanner.scan_results['files'])} 个文件")

        # 交互式下载
        if self.scanner.scan_results["downloadable_files"]:
            print(f"   可下载文件: {len(self.scanner.scan_results['downloadable_files'])} 个")
            choice = input("是否开始下载所有文件? (y/n): ").strip().lower()
            if choice == 'y':
                # 触发下载，CDP 负责监控状态
                for info in self.scanner.scan_results["downloadable_files"]:
                    await self._trigger_right_click_download(page, info)
                print("⏳ 正在监控下载... 按 Ctrl+C 停止查看")
                while any(t.status == DownloadStatus.DOWNLOADING for t in self.status_manager.tasks.values()):
                    await asyncio.sleep(1)

    async def test_download_on_current_page(self):
        pages = self.scanner.context.pages
        if not pages:
            print("❌ 无可用页面")
            return
        page = pages[0]
        await self._attach_cdp_to_page(page)
        print(f"✅ 使用页面: {await page.title()}")
        input("按回车键在页面中手动触发下载，然后在此窗口查看进度...")
        print("🛰️ 开始监听... 按 Ctrl+C 退出")
        while True:
            await asyncio.sleep(1)

    async def _open_page(self, url: str):
        page = await self.scanner.context.new_page()
        self.scanner.created_pages.append(page)
        if not await navigate_to_url(page, url):
            raise RuntimeError("页面导航失败")
        await check_login_required(page)
        info = await get_page_info(page)
        self.scanner.scan_results["debug_info"]["page_info"].update(info)
        return page

    async def _trigger_right_click_download(self, page, file_info):
        # 复用现有 downloader 的右键菜单查找逻辑会更稳，这里简化为点击文本/定位符可选
        try:
            # 尝试通过文本定位右键菜单
            x = file_info['position']['x'] + file_info['position']['width'] / 2
            y = file_info['position']['y'] + file_info['position']['height'] / 2
            await page.mouse.move(x, y)
            await page.mouse.click(x, y, button='right')
            # 点击“下载”
            download_option = page.locator('text="下载"').first
            if await download_option.count() == 0:
                download_option = page.locator('text="Download"').first
            await download_option.click()
        except Exception as e:
            print(f"⚠️ 触发下载失败: {e}")

async def main():
    if len(sys.argv) <= 1:
        print("用法: python scripts/scan_with_cdp_download_monitor.py [scan|test|status|cleanup]")
        return

    cmd = sys.argv[1].lower()
    if cmd == 'scan':
        # 与 scripts/scan_with_existing_browser.py 保持完全一致的默认目标 URL
        target_url = (
            "https://scautoeng.sharepoint.com/sites/KOTEI-SCAE/Shared%20Documents/Forms/AllItems.aspx"
            "?id=%2Fsites%2FKOTEI%2DSCAE%2FShared%20Documents%2FGEN1%2E5%E4%B8%AD%E5%9B%BDFOT%2F%E3%83%87%E3%83%BC%E3%82%BF%E8%A7%A3%E6%9E%90%2F%E8%AA%8D%E8%AD%98%E7%B3%BB%2F%E8%B5%B0%E8%B7%AF%E8%AA%8D%E8%AD%98%2F%E3%82%B9%E3%82%AF%E3%83%AA%E3%83%97%E3%83%88%E6%A4%9C%E8%A8%8E%2FTest"
            "&viewid=8e19c37a%2Dacdb%2D4c40%2Da22e%2D92e27e7e3366&csf=1&web=1&e=NWcbWt&FolderCTID=0x01200090D0082931AED242A8680C59FF4AF68D"
        )
        async with ScanWithCdpDownloadMonitor() as app:
            await app.scan_then_optionally_download(target_url)
    elif cmd == 'test':
        async with ScanWithCdpDownloadMonitor() as app:
            await app.test_download_on_current_page()
    elif cmd == 'status':
        mgr = create_download_status_manager(STATE_FILE)
        try:
            summary = mgr.get_summary()
            print("📊 下载摘要:")
            print(summary)
        finally:
            mgr.close()
    elif cmd == 'cleanup':
        mgr = create_download_status_manager(STATE_FILE)
        try:
            mgr.cleanup_completed_tasks(0)
        finally:
            mgr.close()
    else:
        print(f"未知命令: {cmd}")

if __name__ == '__main__':
    asyncio.run(main())
