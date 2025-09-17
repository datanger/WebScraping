#!/usr/bin/env python3
"""
SharePoint 文件结构扫描器 - 使用现有浏览器
业务逻辑脚本，专注于核心业务流程
"""

import asyncio
import sys

sys.path.append('.')
from playwright.async_api import async_playwright
from src.sp_automation.sharepoint_scanner import SharePointScanner
from src.sp_automation.recursive_scanner import SharePointRecursiveScanner
from src.sp_automation.file_downloader import SharePointFileDownloader
from src.sp_automation.page_operations import navigate_to_url, check_login_required, get_page_info


class SharePointExistingBrowserScanner:
    """SharePoint 文件结构扫描器 - 业务逻辑封装"""
    
    def __init__(self, test_mode: bool = True, debug_port: int = 9222):
        self.test_mode = test_mode
        self.debug_port = debug_port
        self.scanner = SharePointScanner(test_mode, debug_port)
        self.recursive_scanner = None
        self.downloader = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        playwright = await async_playwright().start()
        success = await self.scanner.connect_to_browser(playwright)
        if success:
            self.recursive_scanner = SharePointRecursiveScanner(self.scanner)
            self.downloader = SharePointFileDownloader(self.scanner.safety_manager)
            return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.scanner.cleanup_pages()
        await self.scanner.disconnect()
    
    async def wait_for_login_and_scan(self, url: str, recursive: bool = True):
        """等待用户登录并扫描 SharePoint 文件结构"""
        print(f"🔍 开始扫描 SharePoint 文件结构")
        print(f"   目标路径: {url.split('/')[-1] if '/' in url else url}")
        print(f"   测试模式: {'启用' if self.test_mode else '禁用'}")
        print()
        
        page = None
        try:
            # 解析 URL 路径信息
            path_info = self.scanner.safety_manager.parse_sharepoint_url(url)
            self.scanner.scan_results["target_url"] = url
            self.scanner.scan_results["path_info"] = path_info
            
            # 创建新标签页
            page = await self.scanner.context.new_page()
            self.scanner.created_pages.append(page)
            
            # 导航到页面
            if not await navigate_to_url(page, url):
                raise Exception("页面导航失败")
            
            # 获取页面信息
            page_info = await get_page_info(page)
            self.scanner.scan_results["debug_info"]["page_info"].update(page_info)
            
            # 检查是否需要登录
            await check_login_required(page)
            
            # 开始递归扫描
            if recursive:
                await self.recursive_scanner.recursive_scan_folders(page, url, current_path="")
            else:
                # 只扫描当前页面
                elements = await self.scanner.scan_page_elements(page)
                for element in elements:
                    if not element['visible'] or not element['text']:
                        continue
                    
                    element_type = self.scanner.classify_element(element)
                    
                    if element_type == "folder":
                        self.scanner.scan_results["folders"].append({
                            "name": element['text'],
                            "type": "folder",
                            "position": element['position'],
                            "href": element['href'],
                            "index": len(self.scanner.scan_results["folders"])
                        })
                    elif element_type == "file":
                        self.scanner.scan_results["files"].append({
                            "name": element['text'],
                            "type": "file",
                            "position": element['position'],
                            "href": element['href'],
                            "index": len(self.scanner.scan_results["files"])
                        })
            
            # 更新扫描状态
            self.scanner.scan_results["scan_status"] = "completed"
            self.scanner.scan_results["total_items"] = len(self.scanner.scan_results["folders"]) + len(self.scanner.scan_results["files"])
            
            print(f"\n✅ 扫描完成")
            print(f"   发现: {len(self.scanner.scan_results['folders'])} 个文件夹, {len(self.scanner.scan_results['files'])} 个文件")
            
            return self.scanner.scan_results
            
        except Exception as e:
            print(f"❌ 扫描失败: {e}")
            self.scanner.scan_results["scan_status"] = "failed"
            self.scanner.scan_results["error"] = str(e)
            return self.scanner.scan_results
        finally:
            # 确保关闭新创建的标签页，但保留至少一个标签页以维持浏览器运行
            if page and not page.is_closed():
                try:
                    if self.scanner.context and len(self.scanner.context.pages) > 1:
                        await page.close()
                        print("📄 新标签页已关闭")
                    else:
                        print("⚠️ 检测到只有一个标签页，保留以维持浏览器运行")
                        print(f"📄 保留标签页: {page.url}")
                except Exception as e:
                    print(f"⚠️ 关闭标签页时出错: {e}")
    
    async def cleanup_pages(self):
        """手动清理所有新创建的标签页"""
        await self.scanner.cleanup_pages()
    
    def save_results(self, output_file: str = "sharepoint_structure_scan.json"):
        """保存扫描结果"""
        self.scanner.save_results(output_file)


async def test_right_click_download():
    """测试右键下载功能"""
    print("🧪 测试右键下载功能")
    print("=" * 50)
    print("🔒 安全提醒：本脚本严格遵循 SharePoint 安全操作指南")
    print("   ✅ 只允许下载操作")
    print("   ❌ 禁止删除、移动、重命名等危险操作")
    print("   🛡️ 所有操作都需要用户确认")
    print("=" * 50)
    
    async with SharePointExistingBrowserScanner(test_mode=True, debug_port=9222) as scanner:
        try:
            # 获取页面对象
            if scanner.scanner.context and scanner.scanner.context.pages:
                # 选择 SharePoint 页面而不是下载页面
                sharepoint_page = None
                for page in scanner.scanner.context.pages:
                    title = await page.title()
                    url = page.url
                    if 'sharepoint.com' in url or 'KOTEI' in title:
                        sharepoint_page = page
                        break
                
                if not sharepoint_page:
                    sharepoint_page = scanner.scanner.context.pages[0]
                
                page = sharepoint_page
                print(f"✅ 使用页面: {await page.title()}")
                
                # 等待用户确认
                input("按回车键开始测试右键下载...")
                
                # 查找文件元素
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
                    # 让用户选择要测试的元素
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
                    
                    # 创建文件信息
                    file_info = {
                        "name": test_element['text'],
                        "position": test_element['position']
                    }
            
            # 执行右键下载
                    success = await scanner.downloader.download_file_by_right_click(page, file_info)
                    
                    if success:
                        print("✅ 右键下载测试成功")
                    else:
                        print("❌ 右键下载测试失败")
                else:
                    print("❌ 未找到可测试的元素")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """主函数"""
    # 目标 URL
    target_url = "https://scautoeng.sharepoint.com/sites/KOTEI-SCAE/Shared%20Documents/Forms/AllItems.aspx?id=%2Fsites%2FKOTEI%2DSCAE%2FShared%20Documents%2FGEN1%2E5%E4%B8%AD%E5%9B%BDFOT%2F%E3%83%87%E3%83%BC%E3%82%BF%E8%A7%A3%E6%9E%90%2F%E8%AA%8D%E8%AD%98%E7%B3%BB%2F%E8%B5%B0%E8%B7%AF%E8%AA%8D%E8%AD%98%2F%E3%82%B9%E3%82%AF%E3%83%AA%E3%83%97%E3%83%88%E6%A4%9C%E8%A8%8E%2FTest&viewid=8e19c37a%2Dacdb%2D4c40%2Da22e%2D92e27e7e3366&csf=1&web=1&e=NWcbWt&FolderCTID=0x01200090D0082931AED242A8680C59FF4AF68D"
    
    print("🚀 SharePoint 文件结构扫描器 (使用现有浏览器)")
    print("=" * 60)
    print("🔒 安全提醒：本脚本严格遵循 SharePoint 安全操作指南")
    print("   ✅ 只允许查看、预览、下载等只读操作")
    print("   ❌ 严格禁止删除、移动、重命名等危险操作")
    print("   🛡️ 测试模式下所有操作都需要用户确认")
    print("=" * 60)
    
    async with SharePointExistingBrowserScanner(test_mode=True, debug_port=9222) as scanner:
        try:
            # 执行递归扫描
            results = await scanner.wait_for_login_and_scan(target_url, recursive=True)
            
            # 保存结果
            scanner.save_results()
        finally:
            # 确保清理所有新创建的标签页
            await scanner.cleanup_pages()
        
        # 显示最终结果
        if results['scan_status'] == 'completed':
            print(f"\n✅ 扫描完成")
            print(f"   发现: {len(scanner.scanner.scan_results['folders'])} 个文件夹, {len(scanner.scanner.scan_results['files'])} 个文件")
            
            # 提供下载选项
            if scanner.scanner.scan_results["downloadable_files"]:
                print(f"   可下载文件: {len(scanner.scanner.scan_results['downloadable_files'])} 个")
                
                download_choice = input("\n是否开始下载文件? (y/n): ").strip().lower()
                if download_choice == 'y':
                    # 获取页面对象用于下载
                    if scanner.scanner.context and scanner.scanner.context.pages:
                        page = scanner.scanner.context.pages[0]
                        await scanner.downloader.download_files_interactive(page, scanner.scanner.scan_results["downloadable_files"])
                        
                        # 显示下载摘要
                        download_summary = scanner.downloader.get_download_summary()
                        print(f"\n📊 下载完成: {download_summary['successful_downloads']}/{download_summary['total_downloads']} 成功")
                    else:
                        print("❌ 无法获取页面对象进行下载")
        else:
            print(f"\n❌ 扫描失败: {results.get('error', '未知错误')}")


if __name__ == "__main__":
    import sys
    
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # 运行测试模式
        asyncio.run(test_right_click_download())
    else:
        # 运行正常扫描
        asyncio.run(main())
