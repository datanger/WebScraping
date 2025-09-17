#!/usr/bin/env python3
"""
SharePoint 文件下载器模块
提供安全的文件下载功能
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from playwright.async_api import Page

from .safe_operations import SharePointSafetyManager
from .config import settings


class SharePointFileDownloader:
    """SharePoint 文件下载器"""
    
    def __init__(self, safety_manager: SharePointSafetyManager):
        """
        初始化下载器
        
        Args:
            safety_manager: 安全管理器实例
        """
        self.safety_manager = safety_manager
        self.download_history = []
    
    async def download_file_by_right_click(self, page: Page, file_info: Dict[str, Any]) -> bool:
        """右键下载文件（根据配置选择下载方法）"""
        if settings.download_method == "browser_default":
            return await self._download_with_browser_default(page, file_info)
        else:
            return await self._download_with_interception(page, file_info)
    
    async def _download_with_browser_default(self, page: Page, file_info: Dict[str, Any]) -> bool:
        """使用浏览器默认下载行为，但确保下载完成"""
        try:
            # 查找文件元素
            file_element = await self._find_file_element(page, file_info)
            if not file_element:
                print(f"   ❌ 未找到文件元素: {file_info['name']}")
                return False
            
            # 滚动到文件位置确保可见
            await file_element.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            
            # 右键点击文件
            print(f"   🖱️ 右键点击: {file_info['name']}")
            await file_element.click(button="right")
            await page.wait_for_timeout(1000)  # 等待右键菜单出现
            
            # 查找下载选项
            download_option = await self._find_download_option_in_menu(page)
            if not download_option:
                print("   ❌ 未找到下载选项")
                return False
            
            # 安全检查：确认是下载操作而不是其他危险操作
            download_text = await download_option.inner_text()
            safe_actions = ["下载", "Download", "下載"]
            if not any(safe_action in download_text for safe_action in safe_actions):
                print(f"   ⚠️ 安全警告：检测到非下载操作 '{download_text}'")
                print("   🔒 根据安全指南，只允许下载操作")
                return False
            
            # 在测试模式下，需要用户确认下载操作
            if self.safety_manager.test_mode:
                # 等待用户确认
                print(f"   ❓ 下载 '{file_info['name']}'? (y/n/s): ", end="", flush=True)
                user_input = input().strip().lower()
                
                if user_input in ['n', 'no', '否']:
                    print(f"   ⏭️ 取消下载: {file_info['name']}")
                    return False
                elif user_input in ['s', 'skip', '跳过']:
                    print(f"   ⏭️ 跳过所有后续下载确认")
                    self.safety_manager.test_mode = False  # 禁用测试模式
                elif user_input not in ['y', 'yes', '是']:
                    print(f"   ⏭️ 无效输入，取消下载: {file_info['name']}")
                    return False
            
            # 设置下载路径
            downloads_dir = Path.home() / "Downloads"
            if settings.download_path:
                downloads_dir = Path(settings.download_path)
            downloads_dir.mkdir(parents=True, exist_ok=True)
            
            # 使用 expect_download 来确保下载完成，但使用浏览器建议的文件名
            print("   📥 开始下载...")
            async with page.expect_download(timeout=30000) as download_info:
                await download_option.click()
            
            download = await download_info.value
            
            # 使用浏览器建议的文件名
            suggested_name = download.suggested_filename
            if suggested_name:
                save_path = downloads_dir / suggested_name
            else:
                # 如果没有建议名称，使用原始名称
                original_name = file_info['name']
                save_path = downloads_dir / original_name
            
            # 保存文件
            await download.save_as(save_path)
            
            # 检查文件是否成功保存
            if save_path.exists():
                file_size = save_path.stat().st_size
                if file_size > 0:
                    print(f"   ✅ 下载成功: {suggested_name or file_info['name']} ({file_size} 字节)")
                    print(f"   📁 保存位置: {save_path}")
                    
                    # 记录下载历史
                    self.download_history.append({
                        "file_name": file_info['name'],
                        "save_path": str(save_path),
                        "download_time": datetime.now().isoformat(),
                        "success": True,
                        "method": "browser_default_with_interception"
                    })
                    
                    return True
                else:
                    print("   ⚠️ 文件大小为0，下载失败")
                    return False
            else:
                print("   ❌ 文件保存失败")
                return False
            
        except Exception as e:
            print(f"   ❌ 右键下载失败: {e}")
            self.download_history.append({
                "file_name": file_info['name'],
                "save_path": "",
                "download_time": datetime.now().isoformat(),
                "success": False,
                "error": str(e)
            })
            return False

    async def _download_with_interception(self, page: Page, file_info: Dict[str, Any]) -> bool:
        """通过拦截下载事件进行下载"""
        try:
            # 查找文件元素
            file_element = await self._find_file_element(page, file_info)
            if not file_element:
                print(f"   ❌ 未找到文件元素: {file_info['name']}")
                return False
            
            # 滚动到文件位置确保可见
            await file_element.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            
            # 右键点击文件
            print(f"   🖱️ 右键点击: {file_info['name']}")
            await file_element.click(button="right")
            await page.wait_for_timeout(1000)  # 等待右键菜单出现
            
            # 查找下载选项
            download_option = await self._find_download_option_in_menu(page)
            if not download_option:
                print("   ❌ 未找到下载选项")
                return False
            
            # 安全检查：确认是下载操作而不是其他危险操作
            download_text = await download_option.inner_text()
            safe_actions = ["下载", "Download", "下載"]
            if not any(safe_action in download_text for safe_action in safe_actions):
                print(f"   ⚠️ 安全警告：检测到非下载操作 '{download_text}'")
                print("   🔒 根据安全指南，只允许下载操作")
                return False
            
            # 在测试模式下，需要用户确认下载操作
            if self.safety_manager.test_mode:
                # 等待用户确认
                print(f"   ❓ 下载 '{file_info['name']}'? (y/n/s): ", end="", flush=True)
                user_input = input().strip().lower()
                
                if user_input in ['n', 'no', '否']:
                    print(f"   ⏭️ 取消下载: {file_info['name']}")
                    return False
                elif user_input in ['s', 'skip', '跳过']:
                    print(f"   ⏭️ 跳过所有后续下载确认")
                    self.safety_manager.test_mode = False  # 禁用测试模式
                elif user_input not in ['y', 'yes', '是']:
                    print(f"   ⏭️ 无效输入，取消下载: {file_info['name']}")
                    return False
            
            # 点击下载选项并等待下载
            print("   📥 开始下载...")
            
            # 使用 expect_download 来正确处理下载事件
            async with page.expect_download(timeout=30000) as download_info:
                await download_option.click()
            
            download = await download_info.value
            
            # 生成保存路径
            downloads_dir = Path.home() / "Downloads"
            downloads_dir.mkdir(parents=True, exist_ok=True)
            
            # 使用浏览器建议的文件名，保持原始格式
            suggested_name = download.suggested_filename
            if suggested_name:
                save_path = downloads_dir / suggested_name
            else:
                # 如果没有建议名称，使用原始名称
                original_name = file_info['name']
                save_path = downloads_dir / original_name
            
            # 保存文件
            await download.save_as(save_path)
            
            # 检查文件大小
            if save_path.exists():
                file_size = save_path.stat().st_size
                if file_size > 0:
                    print(f"   ✅ 下载成功: {suggested_name or file_info['name']} ({file_size} 字节)")
                    
                    # 记录下载历史
                    self.download_history.append({
                        "file_name": file_info['name'],
                        "save_path": str(save_path),
                        "file_size": file_size,
                        "download_time": datetime.now().isoformat(),
                        "success": True
                    })
                    
                    return True
                else:
                    print("   ⚠️ 文件大小为0，下载失败")
                    return False
            else:
                print("   ❌ 文件保存失败")
                return False
            
        except Exception as e:
            print(f"   ❌ 右键下载失败: {e}")
            
            # 记录失败历史
            self.download_history.append({
                "file_name": file_info['name'],
                "error": str(e),
                "download_time": datetime.now().isoformat(),
                "success": False
            })
            
            return False
    
    async def _find_file_element(self, page: Page, file_info: Dict[str, Any]):
        """查找文件元素"""
        # 尝试多种选择器找到文件
        selectors = [
            f'text="{file_info["name"]}"',
            f'[title="{file_info["name"]}"]',
            f'a:has-text("{file_info["name"]}")',
            '.heroTextWithHeroCommandsWrapped2_c5aceefe:has-text("{file_info["name"]}")',
            '.field-LinkFilename-htmlGrid_1:has-text("{file_info["name"]}")'
        ]
        
        for selector in selectors:
            try:
                file_element = page.locator(selector).first
                if await file_element.count() > 0:
                    return file_element
            except Exception:
                continue
        
        return None
    
    async def _find_download_option_in_menu(self, page: Page):
        """在右键菜单中查找下载选项"""
        try:
            # 查找下载选项的多种可能文本
            download_texts = ["下载", "Download", "下載"]
            
            for text in download_texts:
                # 查找包含下载文本的菜单项
                download_option = page.locator(f'text="{text}"').first
                if await download_option.count() > 0 and await download_option.is_visible():
                    print(f"   ✅ 找到下载选项: {text}")
                    return download_option
            
            # 如果文本匹配失败，尝试通过图标查找
            download_icon = page.locator('[data-icon-name="Download"]').first
            if await download_icon.count() > 0 and await download_icon.is_visible():
                print("   ✅ 找到下载图标")
                return download_icon
            
            # 尝试查找包含下载相关的菜单项
            menu_items = page.locator('[role="menuitem"], .ms-ContextualMenu-item')
            item_count = await menu_items.count()
            
            print(f"   🔍 找到 {item_count} 个菜单项")
            for i in range(item_count):
                item = menu_items.nth(i)
                text = await item.inner_text()
                print(f"   {i+1}. {text}")
                if any(download_text in text for download_text in download_texts):
                    print(f"   ✅ 找到下载菜单项: {text}")
                    return item
            
            print("   ❌ 未找到下载选项")
            return None
            
        except Exception as e:
            print(f"   ❌ 查找下载选项失败: {e}")
            return None
    
    async def download_files_interactive(self, page: Page, file_list: List[Dict[str, Any]]):
        """交互式下载文件列表"""
        print(f"\n📥 开始下载 {len(file_list)} 个文件...")
        
        for file_info in file_list:
            # 在测试模式下，需要用户确认每个文件
            if self.safety_manager.test_mode and not getattr(self, 'skip_downloads', False):
                print(f"   下载 '{file_info['name']}'? (y/n/s): ", end="", flush=True)
                confirm = input().strip().lower()
                if confirm == 'n':
                    print("   ⏭️ 跳过")
                    continue
                elif confirm == 's':
                    print("   ⏭️ 跳过所有后续下载")
                    self.skip_downloads = True
                    break
                elif confirm != 'y':
                    print("   ⏭️ 无效输入，跳过")
                    continue
            
            # 执行右键下载
            success = await self.download_file_by_right_click(page, file_info)
            if success:
                # 更新下载状态
                file_info['downloaded'] = True
                file_info['download_time'] = datetime.now().isoformat()
            else:
                print(f"   ❌ 下载失败: {file_info['name']}")
    
    def get_download_summary(self) -> Dict[str, Any]:
        """获取下载摘要"""
        total_downloads = len(self.download_history)
        successful_downloads = len([d for d in self.download_history if d.get('success', False)])
        failed_downloads = total_downloads - successful_downloads
        
        return {
            "total_downloads": total_downloads,
            "successful_downloads": successful_downloads,
            "failed_downloads": failed_downloads,
            "success_rate": (successful_downloads / total_downloads * 100) if total_downloads > 0 else 0,
            "download_history": self.download_history
        }