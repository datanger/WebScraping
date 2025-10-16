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
            
            # 保存文件：优先从浏览器临时文件复制，避免落盘延迟
            tmp_path = await download.path()
            if tmp_path:
                try:
                    import shutil
                    shutil.copyfile(tmp_path, save_path)
                except Exception:
                    await download.save_as(save_path)
            else:
                await download.save_as(save_path)

            # 仅依据浏览器下载器状态判定
            failure_reason = await download.failure()
            if failure_reason is None:
                print(f"   ✅ 下载成功: {suggested_name or file_info['name']}")
                print(f"   📁 保存位置: {save_path}")
                self.download_history.append({
                    "file_name": file_info['name'],
                    "save_path": str(save_path),
                    "download_time": datetime.now().isoformat(),
                    "success": True,
                    "method": "browser_default_with_interception"
                })
                return True
            else:
                print(f"   ❌ 浏览器下载失败: {failure_reason}")
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
            
            # 保存文件：优先从浏览器临时文件复制，避免落盘延迟
            tmp_path = await download.path()
            if tmp_path:
                try:
                    import shutil
                    shutil.copyfile(tmp_path, save_path)
                except Exception:
                    await download.save_as(save_path)
            else:
                await download.save_as(save_path)

            # 仅依据浏览器下载器状态判定
            failure_reason = await download.failure()
            if failure_reason is None:
                print(f"   ✅ 下载成功: {suggested_name or file_info['name']}")
                self.download_history.append({
                    "file_name": file_info['name'],
                    "save_path": str(save_path),
                    "download_time": datetime.now().isoformat(),
                    "success": True
                })
                return True
            else:
                print(f"   ❌ 浏览器下载失败: {failure_reason}")
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
        """查找文件元素 - 改进版本，更精确的定位，避免并发冲突"""
        file_name = file_info["name"]
        
        # 首先尝试精确匹配，避免点击错误的元素
        selectors = [
            # 精确文本匹配，确保完全匹配
            f'text="{file_name}"',
            f'[title="{file_name}"]',
            # 在文件行中查找，确保在正确的行中
            f'.row_e4dc14da:not(.headerRow_e4dc14da) .heroTextWithHeroCommandsWrapped2_c5aceefe:has-text("{file_name}")',
            f'.row_e4dc14da:not(.headerRow_e4dc14da) .field-LinkFilename-htmlGrid_1:has-text("{file_name}")',
            # 在数据行中查找
            f'[role="row"]:not(.headerRow_e4dc14da) .heroTextWithHeroCommandsWrapped2_c5aceefe:has-text("{file_name}")',
            f'[role="row"]:not(.headerRow_e4dc14da) .field-LinkFilename-htmlGrid_1:has-text("{file_name}")',
            # 备用选择器
            f'a:has-text("{file_name}")',
            f'.heroTextWithHeroCommandsWrapped2_c5aceefe:has-text("{file_name}")',
            f'.field-LinkFilename-htmlGrid_1:has-text("{file_name}")'
        ]
        
        for selector in selectors:
            try:
                # 获取所有匹配的元素
                elements = page.locator(selector)
                element_count = await elements.count()
                
                if element_count > 0:
                    # 遍历所有匹配的元素，找到最合适的
                    for i in range(element_count):
                        file_element = elements.nth(i)
                        
                        # 验证元素是否可见且可点击
                        if await file_element.is_visible():
                            # 额外验证：确保这是正确的文件元素
                            element_text = await file_element.inner_text()
                            
                            # 精确匹配文件名，避免部分匹配
                            if element_text.strip() == file_name:
                                # 额外验证：确保元素在正确的行中
                                try:
                                    # 检查父元素是否是文件行
                                    parent_row = file_element.locator('xpath=ancestor::*[contains(@class, "row_e4dc14da") or @role="row"]')
                                    if await parent_row.count() > 0:
                                        # 确保不是表头行
                                        parent_class = await parent_row.get_attribute('class')
                                        if parent_class and 'headerRow_e4dc14da' not in parent_class:
                                            print(f"   ✅ 找到文件元素: {file_name} (选择器: {selector}, 索引: {i})")
                                            return file_element
                                except Exception:
                                    # 如果父元素检查失败，仍然使用该元素
                                    print(f"   ✅ 找到文件元素: {file_name} (选择器: {selector}, 索引: {i})")
                                    return file_element
                            elif file_name in element_text:
                                # 部分匹配的情况，记录但不使用
                                print(f"   ⚠️ 部分匹配: {file_name} in '{element_text}' (选择器: {selector}, 索引: {i})")
                                continue
                
                if element_count > 0:
                    print(f"   ⚠️ 选择器匹配到 {element_count} 个元素，但都不完全匹配: {selector}")
                    
            except Exception as e:
                print(f"   ⚠️ 选择器失败: {selector} - {e}")
                continue
        
        print(f"   ❌ 未找到文件元素: {file_name}")
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