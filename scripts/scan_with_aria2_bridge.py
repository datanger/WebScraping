#!/usr/bin/env python3
"""
SharePoint 扫描 + aria2 桥接下载（使用外部专业下载器断点续传）
- 严格对齐 scripts/scan_with_cdp_download_monitor.py 的交互与输出
- 差异：在触发下载前附加 Browser→aria2 桥接组件，将浏览器下载切换为 aria2c 后台下载

用法：
  python scripts/scan_with_aria2_bridge.py scan      # 执行扫描并可选择下载（由 aria2 接管）
  python scripts/scan_with_aria2_bridge.py test      # 仅测试在当前页右键选中文件并由 aria2 接管
  python scripts/scan_with_aria2_bridge.py status    # 查看下载摘要（来自 DownloadStatusManager）
  python scripts/scan_with_aria2_bridge.py cleanup   # 清理过期任务
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
from src.sp_automation.browser_aria2_bridge import BrowserToAria2Bridge

STATE_FILE = "downloads/download_state.json"
DEBUG_PORT = 9222


class ScanWithAria2Bridge:
    def __init__(self, debug_port: int = DEBUG_PORT, state_file: str = STATE_FILE):
        self.debug_port = debug_port
        self.state_file = state_file
        self.status_manager = create_download_status_manager(state_file)
        self.playwright = None
        self.scanner = None
        self.recursive = None
        self.bridge = None

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.scanner = SharePointScanner(test_mode=True, debug_port=self.debug_port)
        ok = await self.scanner.connect_to_browser(self.playwright)
        if not ok:
            raise RuntimeError("无法连接到现有浏览器 (9222)")
        self.recursive = SharePointRecursiveScanner(self.scanner)
        self.bridge = BrowserToAria2Bridge(self.status_manager)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.scanner.cleanup_pages()
        await self.scanner.disconnect()
        self.status_manager.close()
        await self.playwright.stop()

    async def _attach_bridge_to_page(self, page):
        await self.bridge.attach_to_page(page, output_dir="downloads", logs_dir="downloads/logs")

    async def scan_then_optionally_download(self, url: str):
        print("🚀 SharePoint 文件结构扫描器 (使用现有浏览器)")
        print("=" * 60)
        print("🔒 安全提醒：本脚本严格遵循 SharePoint 安全操作指南")
        print("   ✅ 只允许查看、预览、下载等只读操作")
        print("   ❌ 严格禁止删除、移动、重命名等危险操作")
        print("   🛡️ 测试模式下所有操作都需要用户确认")
        print("   📊 下载方式：由 aria2c 专业下载器接管（断点续传/多连接）")
        print("=" * 60)
        print("🔍 开始扫描 SharePoint 文件结构")

        page = await self._open_page(url)
        # 在触发下载前附加桥接器
        await self._attach_bridge_to_page(page)

        # 递归扫描
        await self.recursive.recursive_scan_folders(page, url, current_path="")
        print(f"✅ 扫描完成，发现 {len(self.scanner.scan_results['files'])} 个文件")

        # 交互式下载（由 aria2 接管）
        if self.scanner.scan_results["downloadable_files"]:
            print(f"   可下载文件: {len(self.scanner.scan_results['downloadable_files'])} 个")
            choice = input("是否开始下载所有文件? (y/n): ").strip().lower()
            if choice == 'y':
                for info in self.scanner.scan_results["downloadable_files"]:
                    await self._trigger_right_click_download(page, info)
                print("⏳ 正在由 aria2 接管下载... 可在 downloads/logs/ 查看日志。按 Ctrl+C 停止查看")
                while any(t.status in (DownloadStatus.DOWNLOADING,) for t in self.status_manager.tasks.values()):
                    await asyncio.sleep(1)

    async def test_download_on_current_page(self):
        """测试右键下载功能（与原脚本 test 交互完全一致，aria2 接管）"""
        print("🧪 测试右键下载功能")
        print("=" * 50)
        print("🔒 安全提醒：本脚本严格遵循 SharePoint 安全操作指南")
        print("   ✅ 只允许下载操作")
        print("   ❌ 禁止删除、移动、重命名等危险操作")
        print("   🛡️ 所有操作都需要用户确认")
        print("   📊 下载方式：由 aria2c 专业下载器接管（断点续传/多连接）")
        print("=" * 50)

        # 获取页面对象（与原脚本一致的选择逻辑）
        ctx = self.scanner.context
        if not ctx or not ctx.pages:
            print("❌ 无可用页面")
            return

        # 选择 SharePoint 页面而不是下载页面
        sharepoint_page = None
        for p in ctx.pages:
            title = await p.title()
            url = p.url
            if 'sharepoint.com' in url or 'KOTEI' in title:
                sharepoint_page = p
                break
        if not sharepoint_page:
            sharepoint_page = ctx.pages[0]
        page = sharepoint_page
        print(f"✅ 使用页面: {await page.title()}")

        # 在触发下载前附加桥接器（aria2 接管）
        await self._attach_bridge_to_page(page)

        # 等待用户确认
        input("按回车键开始测试右键下载...")

        # 查找文件元素（与原脚本一致）
        elements = await page.evaluate("""
            () => {
                const elements = [];
                const seen = new Set();
                const nameCells = document.querySelectorAll('.heroTextWithHeroCommandsWrapped2_c5aceefe');
                nameCells.forEach(cell => {
                    const text = cell.textContent?.trim();
                    if (text && text.length > 0 && text.length < 100) {
                        const headerTexts = ['名称', '修改时间', '修改者', '文件大小', '子文件夹计数', '子项目计数', '创建时间', '创建者'];
                        if (!headerTexts.includes(text) && !seen.has(text)) {
                            seen.add(text);
                            const rect = cell.getBoundingClientRect();
                            elements.push({
                                text: text,
                                position: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
                            });
                        }
                    }
                });
                return elements;
            }
        """)

        print(f"找到 {len(elements)} 个元素:")
        for i, element in enumerate(elements):
            print(f"   {i+1}. {element['text']}")

        if elements:
            print(f"\n请选择要测试下载的元素 (1-{len(elements)}):")
            try:
                choice = int(input("输入数字: ")) - 1
                if 0 <= choice < len(elements):
                    test_element = elements[choice]
                else:
                    print("❌ 无效选择，使用第一个元素")
                    test_element = elements[0]
            except ValueError:
                print("❌ 无效输入，使用第一个元素")
                test_element = elements[0]

            print(f"\n🎯 测试元素: {test_element['text']}")
            print("⚠️ 安全提醒：即将执行右键下载操作")

            # 最终确认
            final_confirm = input("确认要测试下载此文件吗? (y/n): ").strip().lower()
            if final_confirm not in ['y', 'yes', '是']:
                print("⏭️ 用户取消测试")
                return

            file_info = {
                "name": test_element['text'],
                "position": test_element['position']
            }
            # 执行右键下载（aria2 接管）
            success = await self._trigger_right_click_download(page, file_info)
            if success is False:
                print("❌ 右键下载测试失败")
            else:
                print("✅ 右键下载测试已触发（aria2 接管）")
                # 加入监控循环：保持控制台驻留并显示实时进度（由桥接器输出单行进度）
                print("⏳ 正在由 aria2 接管下载... 可在 downloads/logs/ 查看日志。按 Ctrl+C 停止查看")
                try:
                    while any(t.status == DownloadStatus.DOWNLOADING for t in self.status_manager.tasks.values()):
                        await asyncio.sleep(0.5)
                except KeyboardInterrupt:
                    pass
        else:
            print("❌ 未找到可测试的元素")

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
        try:
            x = file_info['position']['x'] + file_info['position']['width'] / 2
            y = file_info['position']['y'] + file_info['position']['height'] / 2
            await page.mouse.move(x, y)
            await page.mouse.click(x, y, button='right')
            download_option = page.locator('text="下载"').first
            if await download_option.count() == 0:
                download_option = page.locator('text="Download"').first
            await download_option.click()
        except Exception as e:
            print(f"⚠️ 触发下载失败: {e}")


async def main():
    if len(sys.argv) <= 1:
        print("用法: python scripts/scan_with_aria2_bridge.py [scan|test|status|cleanup]")
        return

    cmd = sys.argv[1].lower()
    if cmd == 'scan':
        target_url = (
            "https://scautoeng.sharepoint.com/sites/KOTEI-SCAE/Shared%20Documents/Forms/AllItems.aspx"
            "?id=%2Fsites%2FKOTEI%2DSCAE%2FShared%20Documents%2FGEN1%2E5%E4%B8%AD%E5%9B%BDFOT%2F%E3%83%87%E3%83%BC%E3%82%BF%E8%A7%A3%E6%9E%90%2F%E8%AA%8D%E8%AD%98%E7%B3%BB%2F%E8%B5%B0%E8%B7%AF%E8%AA%8D%E8%AD%98%2F%E3%82%B9%E3%82%AF%E3%83%AA%E3%83%97%E3%83%88%E6%A4%9C%E8%A8%8E%2FTest"
            "&viewid=8e19c37a%2Dacdb%2D4c40%2Da22e%2D92e27e7e3366&csf=1&web=1&e=NWcbWt&FolderCTID=0x01200090D0082931AED242A8680C59FF4AF68D"
        )
        async with ScanWithAria2Bridge() as app:
            await app.scan_then_optionally_download(target_url)
    elif cmd == 'test':
        async with ScanWithAria2Bridge() as app:
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


