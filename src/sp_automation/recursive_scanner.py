#!/usr/bin/env python3
"""
SharePoint 递归扫描器模块
提供文件夹递归扫描功能
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from playwright.async_api import Page

from .sharepoint_scanner import SharePointScanner
from .page_operations import find_element_by_text, click_element_with_confirmation, collect_downloadable_files


class SharePointRecursiveScanner:
    """SharePoint 递归扫描器"""
    
    def __init__(self, scanner: SharePointScanner):
        """
        初始化递归扫描器
        
        Args:
            scanner: SharePoint 扫描器实例
        """
        self.scanner = scanner
    
    async def recursive_scan_folders(self, page: Page, current_url: str, current_path: str = "", depth: int = 0, zip_found_callback: Optional[Any] = None):
        """递归扫描文件夹"""
        print(f"\n📁 扫描: {current_path or '根目录'}")
        
        # 直接扫描当前页面的文件和文件夹，避免重复
        current_page_folders = []
        current_page_files = []
        
        # 扫描页面元素，只获取当前页面的内容
        elements = await page.evaluate("""
            () => {
                const getElementInfo = (element, type) => {
                    const rect = element.getBoundingClientRect();
                    return {
                        text: (element.textContent || "").trim(),
                        tagName: element.tagName.toLowerCase(),
                        className: element.className || '',
                        id: element.id || '',
                        href: element.href || '',
                        visible: rect.width > 0 && rect.height > 0,
                        position: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
                        type: type,
                        title: element.title || '',
                        ariaLabel: element.getAttribute('aria-label') || ''
                    };
                };

                const allElements = [];
                const seen = new Set(); // 用于去重
                
                // 优先查找最具体的文本元素，避免重复
                const nameCells = document.querySelectorAll('.heroTextWithHeroCommandsWrapped2_c5aceefe');
                nameCells.forEach(cell => {
                    const text = cell.textContent?.trim();
                    if (text && text.length > 0 && text.length < 100) {
                        // 排除表头文本
                        const headerTexts = ['名称', '修改时间', '修改者', '文件大小', '子文件夹计数', '子项目计数', '创建时间', '创建者'];
                        if (headerTexts.includes(text)) {
                            return; // 跳过表头
                        }
                        
                        // 检查是否在数据行中（不是表头行）
                        const row = cell.closest('.row_e4dc14da, [role="row"]');
                        if (row && row.classList.contains('headerRow_e4dc14da')) {
                            return; // 跳过表头行
                        }
                        
                        // 去重：避免重复添加相同的文本
                        if (seen.has(text)) {
                            return;
                        }
                        seen.add(text);
                        
                        // 判断是文件夹还是文件
                        let itemType = 'unknown';
                        
                        if (row) {
                            const rowClass = row.className;
                            if (rowClass.includes('filesRow_15806f83')) {
                                itemType = 'folder_item';
                            }
                        }
                        
                        // 基于文本内容判断
                        if (text.match(/^d{6}$/) || text.match(/^d{4}d{2}$/) || text.includes('_走行データ送付')) {
                            itemType = 'folder_item';
                        } else if (text.includes('.')) {
                            itemType = 'file_item';
                        }
                        
                        // 只添加有效的文件/文件夹项目
                        if (itemType !== 'unknown') {
                            allElements.push(getElementInfo(cell, itemType));
                        }
                    }
                });
                
                // 如果主要选择器没找到元素，使用备用选择器
                if (allElements.length === 0) {
                    const fallbackCells = document.querySelectorAll('.field-LinkFilename-htmlGrid_1');
                    fallbackCells.forEach(cell => {
                        const text = cell.textContent?.trim();
                        if (text && text.length > 0 && text.length < 100) {
                            const headerTexts = ['名称', '修改时间', '修改者', '文件大小', '子文件夹计数', '子项目计数', '创建时间', '创建者'];
                            if (headerTexts.includes(text)) {
                                return; // 跳过表头
                            }
                            
                            const row = cell.closest('.row_e4dc14da, [role="row"]');
                            if (row && row.classList.contains('headerRow_e4dc14da')) {
                                return; // 跳过表头行
                            }
                            
                            if (seen.has(text)) {
                                return; // 去重
                            }
                            seen.add(text);
                            
                            let itemType = 'unknown';
                            if (row) {
                                const rowClass = row.className;
                                if (rowClass.includes('filesRow_15806f83')) {
                                    itemType = 'folder_item';
                                }
                            }
                            
                            if (text.match(/^d{6}$/) || text.match(/^d{4}d{2}$/) || text.includes('_走行データ送付')) {
                                itemType = 'folder_item';
                            } else if (text.includes('.')) {
                                itemType = 'file_item';
                            }
                            
                            if (itemType !== 'unknown') {
                                allElements.push(getElementInfo(cell, itemType));
                            }
                        }
                    });
                }
                
                return allElements;
            }
        """)
        
        # 分类当前页面的元素
        for element in elements:
            if not element['visible'] or not element['text']:
                continue
            
            element_type = self.scanner.classify_element(element)
            
            if element_type == "folder":
                folder_name = element['text']
                folder_path = f"{current_path}/{folder_name}" if current_path else folder_name
                
                folder_info = {
                    "name": folder_name,
                    "type": "folder",
                    "position": element['position'],
                    "href": element['href'],
                    "full_path": folder_path,
                    "depth": depth
                }
                current_page_folders.append(folder_info)
                self.scanner.scan_results["folders"].append(folder_info)
                
            elif element_type == "file":
                file_name = element['text']
                file_path = f"{current_path}/{file_name}" if current_path else file_name
                
                file_info = {
                    "name": file_name,
                    "type": "file",
                    "position": element['position'],
                    "href": element['href'],
                    "full_path": file_path,
                    "depth": depth
                }
                current_page_files.append(file_info)
                self.scanner.scan_results["files"].append(file_info)

        # 在进入/扫描当前层后，若提供回调，则把当前层的 .zip 直接回调打印/保存
        if callable(zip_found_callback):
            try:
                page_url = page.url
            except Exception:
                page_url = current_url
            for f in current_page_files:
                name = f.get("name") or ""
                if isinstance(name, str) and name.lower().endswith('.zip'):
                    info = {
                        "text": name,
                        "path": current_path,
                        "href": f.get("href") or "",
                        "page_url": page_url,
                        "position": f.get("position") or {}
                    }
                    try:
                        await zip_found_callback(info)
                    except TypeError:
                        # 兼容同步回调
                        zip_found_callback(info)
        
        # 实时更新并显示完整的文件架构
        self._display_current_file_tree()
        
        # 收集当前页面的可下载文件
        downloadable_files = await collect_downloadable_files(page, current_path)
        self.scanner.scan_results["downloadable_files"].extend(downloadable_files)
        
        # 询问用户是否要下载当前页面的文件
        if downloadable_files:
            await self._offer_download_current_page(page, downloadable_files)
        
        # 递归处理每个文件夹
        for folder in current_page_folders:
            folder_name = folder['name']
            folder_path = folder['full_path']
            
            # 尝试点击文件夹进入
            if await self._click_folder_and_scan(page, folder, folder_path, depth):
                # 成功进入文件夹，递归扫描
                new_url = page.url
                await self.recursive_scan_folders(page, new_url, folder_path, depth + 1, zip_found_callback=zip_found_callback)
                
                # 返回上级目录
                await self._navigate_back(page, current_url)
                await page.wait_for_timeout(1200)  # 优化：从2000ms缩减为1200ms (3/5)
            else:
                print(f"   ❌ 无法进入文件夹: {folder_name}")
    
    async def _click_folder_and_scan(self, page: Page, folder: Dict[str, Any], folder_path: str, depth: int) -> bool:
        """点击文件夹并进入"""
        folder_name = folder['name']
        
        try:
            # 查找文件夹元素
            folder_element = await find_element_by_text(page, folder_name)
            
            if not folder_element:
                print(f"   ❌ 未找到文件夹元素: {folder_name}")
                return False
            
            # 在测试模式下，需要用户确认
            if not await click_element_with_confirmation(page, folder_element, folder_name, self.scanner.test_mode):
                return False
            
            # 验证是否成功进入文件夹
            current_title = await page.title()
            if folder_name in current_title or "所有文档" in current_title:
                print(f"   ✅ 成功进入文件夹: {folder_name}")
                return True
            else:
                print(f"   ❌ 进入文件夹失败，页面标题: {current_title}")
                return False
                
        except Exception as e:
            print(f"   ❌ 点击文件夹失败: {e}")
            return False
    
    async def _navigate_back(self, page: Page, target_url: str):
        """返回上级目录"""
        try:
            print(f"   ↩️ 返回上级目录...")
            await page.goto(target_url, wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)
            print(f"   ✅ 已返回上级目录")
        except Exception as e:
            print(f"   ❌ 返回上级目录失败: {e}")
    
    async def _offer_download_current_page(self, page: Page, current_page_files: List[Dict[str, Any]]):
        """询问用户是否要下载当前页面的文件"""
        if not current_page_files:
            return
            
        print(f"\n📥 发现 {len(current_page_files)} 个可下载文件")
        print("是否下载? (y/n/s): ", end="", flush=True)
        download_choice = input().strip().lower()
        
        if download_choice == 'y':
            from .file_downloader import SharePointFileDownloader
            downloader = SharePointFileDownloader(self.scanner.safety_manager)
            await downloader.download_files_interactive(page, current_page_files)
        elif download_choice == 's':
            print("⏭️ 跳过所有后续下载确认")
            self.skip_downloads = True
        else:
            print("⏭️ 跳过下载")
    
    def _display_current_file_tree(self):
        """实时显示当前已知的完整文件架构"""
        total_folders = len(self.scanner.scan_results['folders'])
        total_files = len(self.scanner.scan_results['files'])
        downloadable_files = len(self.scanner.scan_results['downloadable_files'])
        
        print(f"\n📊 文件架构 ({total_folders} 文件夹, {total_files} 文件, {downloadable_files} 可下载):")
        print("-" * 50)
        
        # 构建树形结构
        tree_structure = self._build_tree_structure()
        
        # 递归显示树形结构
        self._print_tree_node(tree_structure, 0)
        
        # 显示已下载文件
        downloaded_files = [f for f in self.scanner.scan_results['downloadable_files'] if f.get('downloaded')]
        if downloaded_files:
            print(f"\n✅ 已下载文件 ({len(downloaded_files)} 个):")
            for file_info in downloaded_files:
                print(f"   ✅ {file_info['full_path']}")
        
        print("-" * 50)
    
    def _build_tree_structure(self):
        """构建树形结构"""
        all_items = []
        
        # 添加文件夹
        for folder in self.scanner.scan_results["folders"]:
            all_items.append({
                'name': folder['name'],
                'type': 'folder',
                'depth': folder.get('depth', 0),
                'path': folder.get('full_path', folder['name'])
            })
        
        # 添加文件
        for file in self.scanner.scan_results["files"]:
            all_items.append({
                'name': file['name'],
                'type': 'file',
                'depth': file.get('depth', 0),
                'path': file.get('full_path', file['name'])
            })
        
        # 添加可下载文件（如果不在常规文件列表中）
        for downloadable_file in self.scanner.scan_results["downloadable_files"]:
            file_exists = any(
                file['full_path'] == downloadable_file['full_path'] 
                for file in self.scanner.scan_results["files"]
            )
            
            if not file_exists:
                all_items.append({
                    'name': downloadable_file['name'],
                    'type': 'downloadable_file',
                    'depth': len(downloadable_file['full_path'].split('/')) - 1,
                    'path': downloadable_file['full_path']
                })
        
        # 按路径排序
        all_items.sort(key=lambda x: x['path'])
        
        # 构建树形结构
        tree_structure = {}
        
        for item in all_items:
            path_parts = item['path'].split('/')
            current_level = tree_structure
            
            for i, part in enumerate(path_parts):
                if part not in current_level:
                    current_level[part] = {
                        'type': 'folder' if i < len(path_parts) - 1 else item['type'],
                        'depth': i,
                        'children': {},
                        'is_downloadable': item['type'] == 'downloadable_file'
                    }
                current_level = current_level[part]['children']
        
        return tree_structure
    
    def _print_tree_node(self, node: Dict[str, Any], depth: int):
        """递归打印树节点"""
        for name, info in sorted(node.items()):
            indent = "   " * depth
            
            # 根据类型选择图标
            if info['type'] == 'folder':
                icon = "📁"
            elif info['type'] == 'downloadable_file':
                icon = "📥"
            else:
                icon = "📄"
            
            # 显示节点名称和类型标识
            if info['type'] == 'downloadable_file':
                # 检查是否已下载
                file_info = next((f for f in self.scanner.scan_results['downloadable_files'] if f['full_path'].endswith(name)), None)
                if file_info and file_info.get('downloaded'):
                    icon = "✅"
                    print(f"{indent}{icon} {name} [已下载]")
                else:
                    print(f"{indent}{icon} {name} [可下载]")
            else:
                print(f"{indent}{icon} {name}")
            
            # 递归显示子节点
            if info['children']:
                self._print_tree_node(info['children'], depth + 1)
