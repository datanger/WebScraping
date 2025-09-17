#!/usr/bin/env python3
"""
SharePoint 文件结构扫描器核心模块
提供 SharePoint 文件扫描的核心功能
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from playwright.async_api import Page, Browser, BrowserContext

from .safe_operations import SharePointSafetyManager
from .page_operations import get_page_info


class SharePointScanner:
    """SharePoint 文件结构扫描器核心类"""
    
    def __init__(self, test_mode: bool = True, debug_port: int = 9222):
        """
        初始化扫描器
        
        Args:
            test_mode: 是否启用测试模式
            debug_port: 浏览器调试端口
        """
        self.test_mode = test_mode
        self.debug_port = debug_port
        self.safety_manager = SharePointSafetyManager(
            allowed_download_path="downloads",
            allowed_sharepoint_path="Test",
            test_mode=test_mode
        )
        self.playwright = None
        self.browser = None
        self.context = None
        self.created_pages = []
        self.scan_results = {
            "scan_time": datetime.now().isoformat(),
            "target_url": "",
            "path_info": {},
            "folders": [],
            "files": [],
            "downloadable_files": [],
            "total_items": 0,
            "scan_status": "pending",
            "debug_info": {
                "page_info": {},
                "url_redirects": [],
                "error_details": {},
                "network_logs": [],
                "console_logs": []
            }
        }
    
    async def connect_to_browser(self, playwright) -> bool:
        """连接到现有浏览器"""
        try:
            print(f"🔗 连接到现有浏览器 (端口 {self.debug_port})...")
            self.playwright = playwright
            self.browser = await playwright.chromium.connect_over_cdp(f"http://localhost:{self.debug_port}")
            
            # 获取现有上下文
            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
                pages = self.context.pages
                print(f"✅ 连接到现有浏览器上下文，找到 {len(pages)} 个标签页")
                
                # 显示现有标签页
                for i, page in enumerate(pages):
                    try:
                        title = await page.title()
                        url = page.url
                        print(f"   标签页 {i+1}: {title}")
                        if 'sharepoint' in url.lower():
                            print(f"      ✅ 发现 SharePoint 标签页: {url}")
                    except Exception:
                        print(f"   标签页 {i+1}: 无法获取信息")
            else:
                self.context = await self.browser.new_context()
                print("✅ 创建新的浏览器上下文")
            
            return True
            
        except Exception as e:
            print(f"❌ 连接浏览器失败: {e}")
            print("💡 请确保浏览器以调试模式运行")
            return False
    
    async def disconnect(self):
        """断开浏览器连接"""
        if self.playwright:
            await self.playwright.stop()
    
    async def cleanup_pages(self):
        """清理新创建的标签页"""
        if self.created_pages:
            print("🧹 清理新创建的标签页...")
            
            if self.context:
                total_pages = len(self.context.pages)
                print(f"📊 当前总标签页数量: {total_pages}")
                
                # 如果关闭新标签页后会导致浏览器退出，则保留一个标签页
                if total_pages <= len(self.created_pages):
                    print("⚠️ 检测到关闭所有标签页会导致浏览器退出")
                    print("💡 将保留一个标签页以维持浏览器运行")
                    
                    # 保留最后一个标签页，关闭其他的
                    pages_to_close = self.created_pages[:-1]
                    for page in pages_to_close:
                        try:
                            if not page.is_closed():
                                await page.close()
                                print("📄 已关闭标签页")
                        except Exception as e:
                            print(f"⚠️ 关闭标签页时出错: {e}")
                    
                    # 保留最后一个标签页
                    if self.created_pages:
                        last_page = self.created_pages[-1]
                        print(f"📄 保留标签页以维持浏览器运行: {last_page.url}")
                else:
                    # 正常关闭所有新创建的标签页
                    for page in self.created_pages:
                        try:
                            if not page.is_closed():
                                await page.close()
                                print("📄 已关闭标签页")
                        except Exception as e:
                            print(f"⚠️ 关闭标签页时出错: {e}")
            
            self.created_pages.clear()
            print("✅ 标签页清理完成")
    
    async def scan_page_elements(self, page: Page) -> List[Dict[str, Any]]:
        """扫描页面元素"""
        print("🔍 扫描页面元素...")
        
        try:
            # 等待页面加载完成
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(10000)
            
            # 等待 SharePoint 内容加载
            print("   ⏳ 等待 SharePoint 内容加载...")
            await page.wait_for_timeout(5000)
            
            # 等待 SharePoint 特定元素加载
            try:
                await page.wait_for_selector('[data-automation-id="DetailsRow"], .ms-DetailsRow, [role="row"], .ms-List-cell', timeout=10000)
                print("   ✅ SharePoint 列表元素已加载")
            except:
                print("   ⚠️ 未找到 SharePoint 列表元素，继续扫描...")
            
            # 滚动页面确保所有内容加载
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(2000)
            
            # 检测 SharePoint 页面中的文件和文件夹
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
                            ariaLabel: element.getAttribute('aria-label') || '',
                            parentElement: element.parentElement ? {
                                tagName: element.parentElement.tagName,
                                className: element.parentElement.className,
                                id: element.parentElement.id
                            } : null
                        };
                    };

                    const allElements = [];
                    
                    // 现代 SharePoint 列表项检测
                    const modernSelectors = [
                        '[role="row"]:not(.headerRow_e4dc14da)',
                        '.row_e4dc14da',
                        '.odsp-spartan-cell',
                        '.field-LinkFilename-htmlGrid_1',
                        '.hero_c5aceefe',
                        '.heroTextWithHeroCommandsWrapped2_c5aceefe',
                        '[data-automation-id="DetailsRow"]',
                        '.ms-DetailsRow',
                        '.ms-List-cell',
                        '.ms-DetailsList-cell',
                        'a[href*="id="]',
                        'a[href*="FolderCTID"]',
                        'a[href*="RootFolder"]'
                    ];
                    
                    // 检测现代 SharePoint 列表项
                    modernSelectors.forEach(selector => {
                        try {
                            document.querySelectorAll(selector).forEach(el => {
                                if (el.classList.contains('headerRow_e4dc14da')) {
                                    return;
                                }
                                
                                if (el.tagName.toLowerCase() === 'a') {
                                    allElements.push(getElementInfo(el, 'link'));
                                } else {
                                    const link = el.querySelector('a');
                                    if (link && link.href) {
                                        allElements.push(getElementInfo(link, 'nested_link'));
                                    } else {
                                        const nameElement = el.querySelector('[data-automation-id="DetailsRow-cell"], .ms-DetailsList-cell, .file-name, .folder-name');
                                        if (nameElement) {
                                            const text = nameElement.textContent?.trim();
                                            if (text && text.length > 0 && text.length < 100) {
                                                allElements.push(getElementInfo(nameElement, 'name_element'));
                                            }
                                        }
                                    }
                                }
                            });
                        } catch (e) {
                            console.log('Selector error:', selector, e);
                        }
                    });
                    
                    // 特殊处理：基于调试结果的精确检测
                    try {
                        const nameCells = document.querySelectorAll('.field-LinkFilename-htmlGrid_1, .heroTextWithHeroCommandsWrapped2_c5aceefe');
                        nameCells.forEach(cell => {
                            const text = cell.textContent?.trim();
                            if (text && text.length > 0 && text.length < 100) {
                                let itemType = 'unknown';
                                
                                const row = cell.closest('.row_e4dc14da, [role="row"]');
                                if (row) {
                                    const rowClass = row.className;
                                    if (rowClass.includes('filesRow_15806f83')) {
                                        itemType = 'folder_item';
                                    }
                                }
                                
                                if (text.match(/^d{6}$/) || text.match(/^d{4}d{2}$/)) {
                                    itemType = 'folder_item';
                                } else if (text.includes('.')) {
                                    itemType = 'file_item';
                                }
                                
                                allElements.push(getElementInfo(cell, itemType));
                            }
                        });
                        
                        const dataRows = document.querySelectorAll('[role="row"]:not(.headerRow_e4dc14da)');
                        dataRows.forEach(row => {
                            const nameElement = row.querySelector('.heroTextWithHeroCommandsWrapped2_c5aceefe, .field-LinkFilename-htmlGrid_1');
                            if (nameElement) {
                                const text = nameElement.textContent?.trim();
                                if (text && text.length > 0 && text.length < 100) {
                                    let itemType = 'unknown';
                                    
                                    const rowClass = row.className;
                                    if (rowClass.includes('filesRow_15806f83')) {
                                        itemType = 'folder_item';
                                    }
                                    
                                    if (text.match(/^d{6}$/) || text.match(/^d{4}d{2}$/)) {
                                        itemType = 'folder_item';
                                    }
                                    
                                    allElements.push(getElementInfo(nameElement, itemType));
                                }
                            }
                        });
                        
                    } catch (e) {
                        console.log('Special detection error:', e);
                    }
                    
                    // 去重
                    const uniqueElements = [];
                    const seen = new Set();
                    allElements.forEach(el => {
                        const key = (el.href || '') + el.text + el.type;
                        if (!seen.has(key) && el.text && el.text.length > 0) {
                            seen.add(key);
                            uniqueElements.push(el);
                        }
                    });
                    
                    return uniqueElements;
                }
            """)
            
            print(f"   检测到 {len(elements)} 个元素")
            return elements
            
        except Exception as e:
            print(f"❌ 扫描页面元素失败: {e}")
            return []
    
    def classify_element(self, element: Dict[str, Any]) -> str:
        """分类元素类型"""
        text = element['text'].lower()
        href = element['href'].lower()
        element_type = element.get('type', '')
        
        # 通过元素类型判断（最可靠的方法）
        if element_type in ['folder_item', 'folder_link']:
            return "folder"
        elif element_type in ['file_item', 'file_link']:
            return "file"
        
        # 通过 href 判断
        if 'folderctid' in href:
            return "folder"
        elif 'id=' in href and 'folderctid' not in href:
            return "file"
        
        # 通过父元素和类名判断
        parent_element = element.get('parentElement')
        if parent_element:
            parent_class = parent_element.get('className', '').lower()
            if 'folder' in parent_class or 'directory' in parent_class:
                return "folder"
            elif 'file' in parent_class or 'document' in parent_class:
                return "file"
        
        # 通过文本内容判断
        if any(keyword in text for keyword in ['文件夹', 'folder', '目录', 'directory']):
            return "folder"
        
        # 文件扩展名判断
        if any(ext in text for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.zip', '.rar', '.7z', '.png', '.jpg', '.jpeg', '.gif', '.mp4', '.avi', '.mov']):
            return "file"
        
        # 通过文本模式判断（针对现代SharePoint）
        if len(text) < 50 and not any(ext in text for ext in ['.', 'http', 'www']):
            if text.isdigit() or any(char.isdigit() for char in text):
                return "folder"
        
        return "unknown"
    
    def save_results(self, output_file: str = "sharepoint_structure_scan.json"):
        """保存扫描结果"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 清理数据，移除不可序列化的对象
        cleaned_results = self._clean_results_for_json(self.scan_results)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 扫描结果已保存到: {output_path}")
    
    def _clean_results_for_json(self, data):
        """清理数据以支持JSON序列化"""
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                if hasattr(value, '__await__'):  # 协程对象
                    cleaned[key] = f"<coroutine object: {type(value).__name__}>"
                elif hasattr(value, '__dict__'):  # 复杂对象
                    cleaned[key] = str(value)
                else:
                    cleaned[key] = self._clean_results_for_json(value)
            return cleaned
        elif isinstance(data, list):
            return [self._clean_results_for_json(item) for item in data]
        else:
            return data
