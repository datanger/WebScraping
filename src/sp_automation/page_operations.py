#!/usr/bin/env python3
"""
SharePoint 页面操作模块
提供页面导航、元素查找等通用操作
"""

import asyncio
from typing import Dict, List, Optional, Any
from playwright.async_api import Page


async def get_page_info(page: Page) -> Dict[str, Any]:
    """获取页面基本信息"""
    try:
        return {
            "title": await page.title(),
            "url": page.url,
            "ready_state": await page.evaluate("document.readyState"),
            "domain": await page.evaluate("window.location.hostname"),
            "pathname": await page.evaluate("window.location.pathname"),
            "search": await page.evaluate("window.location.search"),
            "hash": await page.evaluate("window.location.hash"),
            "referrer": await page.evaluate("document.referrer"),
            "user_agent": await page.evaluate("navigator.userAgent"),
            "viewport": await page.evaluate("({width: window.innerWidth, height: window.innerHeight})"),
            "cookies": await page.evaluate("document.cookie"),
            "has_sharepoint_elements": await page.evaluate("""
                () => {
                    const spSelectors = [
                        '[data-automation-id]',
                        '.ms-DetailsRow',
                        '[role="row"]',
                        '.ms-List-cell',
                        '.ms-DetailsList-cell'
                    ];
                    return spSelectors.some(selector => document.querySelector(selector) !== null);
                }
            """)
        }
    except Exception as e:
        return {"error": str(e)}


async def wait_for_sharepoint_loading(page: Page, timeout: int = 10000) -> bool:
    """等待 SharePoint 页面加载完成"""
    try:
        # 等待 SharePoint 特定元素加载
        await page.wait_for_selector('[data-automation-id="DetailsRow"], .ms-DetailsRow, [role="row"], .ms-List-cell', timeout=timeout)
        print("   ✅ SharePoint 列表元素已加载")
        return True
    except:
        print("   ⚠️ 未找到 SharePoint 列表元素，继续扫描...")
        return False


async def scroll_to_load_all_content(page: Page):
    """滚动页面确保所有内容加载"""
    # 滚动到页面底部
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(1200)  # 优化：从2000ms缩减为1200ms (3/5)
    
    # 滚动回顶部
    await page.evaluate("window.scrollTo(0, 0)")
    await page.wait_for_timeout(1200)  # 优化：从2000ms缩减为1200ms (3/5)


async def find_element_by_text(page: Page, text: str, selectors: List[str] = None) -> Optional[Any]:
    """通过文本查找元素"""
    if selectors is None:
        selectors = [
            f'text="{text}"',
            f'[title="{text}"]',
            f'a:has-text("{text}")',
            '.heroTextWithHeroCommandsWrapped2_c5aceefe:has-text("{text}")',
            '.field-LinkFilename-htmlGrid_1:has-text("{text}")'
        ]
    
    for selector in selectors:
        try:
            element = page.locator(selector).first
            if await element.count() > 0:
                return element
        except:
            continue
    
    return None


async def click_element_with_confirmation(page: Page, element: Any, element_name: str, test_mode: bool = True) -> bool:
    """点击元素并支持用户确认"""
    if test_mode:
        print(f"   🎯 找到元素: {element_name}")
        print(f"   ⏳ 准备点击...")
        
        # 悬停到元素上
        await element.hover()
        await page.wait_for_timeout(600)  # 优化：从1000ms缩减为600ms (3/5)
        
        # 等待用户确认
        user_input = input(f"   ❓ 是否点击 '{element_name}'? (y/n/s): ").strip().lower()
        
        if user_input in ['n', 'no', '否']:
            print(f"   ⏭️ 跳过: {element_name}")
            return False
        elif user_input in ['s', 'skip', '跳过']:
            print(f"   ⏭️ 跳过所有后续确认")
            return False
        elif user_input not in ['y', 'yes', '是']:
            print(f"   ⏭️ 无效输入，跳过: {element_name}")
            return False
    
    # 点击元素
    print(f"   🖱️ 点击: {element_name}")
    await element.click()
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(1800)  # 优化：从3000ms缩减为1800ms (3/5)
    
    return True


async def navigate_to_url(page: Page, url: str) -> bool:
    """导航到指定URL"""
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=10000)
        
        if response:
            return True
        else:
            return False
            
    except Exception as e:
        print(f"   ❌ 页面导航失败: {e}")
        return False


async def check_login_required(page: Page) -> bool:
    """检查是否需要登录"""
    current_url = page.url
    if 'login.microsoftonline.com' in current_url or 'login' in current_url.lower():
        print("🔐 需要登录，请在浏览器中完成登录...")
        input("   按回车键继续...")
        
        # 重新获取页面信息
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1200)  # 优化：从2000ms缩减为1200ms (3/5)
        
        return True
    
    return False


async def collect_downloadable_files(page: Page, current_path: str = "") -> List[Dict[str, Any]]:
    """收集当前页面的可下载文件信息"""
    try:
        # 查找所有文件元素
        file_elements = await page.evaluate("""
            () => {
                const files = [];
                
                // 查找文件行
                const fileRows = document.querySelectorAll('.row_e4dc14da:not(.headerRow_e4dc14da)');
                
                fileRows.forEach(row => {
                    const nameCell = row.querySelector('.field-LinkFilename-htmlGrid_1, .heroTextWithHeroCommandsWrapped2_c5aceefe');
                    if (nameCell) {
                        const fileName = nameCell.textContent?.trim();
                        if (fileName && fileName.includes('.')) {  // 只处理有扩展名的文件
                            // 查找下载链接
                            const link = nameCell.querySelector('a[href]');
                            const downloadUrl = link ? link.href : '';
                            
                            // 获取文件信息
                            const fileInfo = {
                                name: fileName,
                                downloadUrl: downloadUrl,
                                position: nameCell.getBoundingClientRect(),
                                rowElement: row
                            };
                            
                            files.push(fileInfo);
                        }
                    }
                });
                
                return files;
            }
        """)
        
        # 处理每个文件
        downloadable_files = []
        for file_info in file_elements:
            if file_info['downloadUrl']:
                full_path = f"{current_path}/{file_info['name']}" if current_path else file_info['name']
                download_file_info = {
                    "name": file_info['name'],
                    "download_url": file_info['downloadUrl'],
                    "full_path": full_path,
                    "position": file_info['position'],
                    "collected_at": asyncio.get_event_loop().time()
                }
                downloadable_files.append(download_file_info)
        
        return downloadable_files
        
    except Exception as e:
        print(f"   ❌ 收集文件下载信息失败: {e}")
        return []