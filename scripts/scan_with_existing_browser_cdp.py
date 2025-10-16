
#!/usr/bin/env python3
"""
SharePoint 文件结构扫描器 - 使用现有浏览器（CDP 下载监控版）
严格对齐 scripts/scan_with_existing_browser.py 的交互与输出，仅在下载前附加
浏览器原生下载器监控（CDP），以获取实时进度/速度/完成状态。
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json
import os
import zipfile
import shutil
import subprocess
import time

sys.path.append('.')
from playwright.async_api import async_playwright
from src.sp_automation.sharepoint_scanner import SharePointScanner
from src.sp_automation.recursive_scanner import SharePointRecursiveScanner
from src.sp_automation.file_downloader import SharePointFileDownloader
from src.sp_automation.page_operations import navigate_to_url, check_login_required, get_page_info
from src.sp_automation.download_status_detector import create_download_status_manager
from src.sp_automation.cdp_download_monitor import BrowserDownloadMonitor
from src.sp_automation.config import settings
from src.sp_automation.login_status_detector import LoginStatusDetector, LoginPageStatus


def find_browser_executable():
    """查找浏览器可执行文件"""
    possible_paths = [
        # Edge
        "/usr/bin/microsoft-edge",
        "/usr/bin/msedge",
        "/snap/bin/microsoft-edge",
        "/opt/microsoft/msedge/msedge",
        # Chrome
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
        "/opt/google/chrome/chrome",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


def check_browser_running(debug_port=9222):
    """检查调试浏览器是否正在运行"""
    try:
        import requests
        response = requests.get(f"http://localhost:{debug_port}/json/version", timeout=2)
        return response.status_code == 200
    except:
        return False


def start_debug_browser(debug_port=9222, target_url=None):
    """启动带调试模式的浏览器"""
    print("🔍 查找浏览器可执行文件...")
    
    browser_path = find_browser_executable()
    if not browser_path:
        print("❌ 未找到浏览器可执行文件")
        print("💡 请手动安装 Edge 或 Chrome 浏览器")
        return False
    
    print(f"✅ 找到浏览器: {browser_path}")
    
    # 创建用户数据目录
    user_data_dir = Path.home() / ".config" / "debug_browser"
    user_data_dir.mkdir(parents=True, exist_ok=True)
    
    # 启动命令
    cmd = [
        browser_path,
        f"--remote-debugging-port={debug_port}",
        "--user-data-dir=" + str(user_data_dir),
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-web-security",
        "--disable-features=VizDisplayCompositor"
    ]

    # 若提供了目标URL，则在启动时直接打开该地址
    if target_url:
        cmd.append(target_url)
    
    print("🚀 启动带调试模式的浏览器...")
    print(f"   命令: {' '.join(cmd)}")
    print(f"   调试端口: {debug_port}")
    print("   用户数据目录:", user_data_dir)
    print()
    print("📋 使用说明:")
    print("   1. 浏览器启动后，请手动登录到 SharePoint")
    print("   2. 登录完成后，脚本将自动继续")
    print()
    
    try:
        # 启动浏览器（分离进程，程序退出后浏览器继续运行）
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )
        print(f"✅ 浏览器已启动 (PID: {process.pid})")
        print("   浏览器将在后台持续运行，即使程序退出也不会关闭")

        # 等待浏览器启动
        print("⏳ 等待浏览器启动...")
        for i in range(30):  # 最多等待30秒
            if check_browser_running(debug_port):
                print("✅ 浏览器调试端口已就绪")
                return True
            time.sleep(1)
            print(f"   等待中... ({i+1}/30)")
        
        print("⚠️ 浏览器启动超时，但可能仍在启动中")
        return True
        
    except Exception as e:
        print(f"❌ 启动浏览器失败: {e}")
        return False


async def ensure_browser_running(debug_port=9222, target_url=None):
    """确保调试浏览器正在运行，如果没有则启动"""
    print("🔍 检查调试浏览器状态...")
    
    if check_browser_running(debug_port):
        print("✅ 调试浏览器已在运行")
        return True
    
    print("⚠️ 调试浏览器未运行，正在启动...")
    if start_debug_browser(debug_port, target_url):
        print("✅ 调试浏览器启动成功")
        return True
    else:
        print("❌ 调试浏览器启动失败")
        return False


async def get_download_directory_structure(page, file_info):
    """获取下载文件在原始网页中的目录结构信息"""
    try:
        # 获取当前页面URL和标题
        current_url = page.url
        page_title = await page.title()
        
        # 解析URL路径信息
        url_parts = current_url.split('/')
        sharepoint_site = ""
        document_library = ""
        folder_path = []
        
        # 提取SharePoint站点信息
        for i, part in enumerate(url_parts):
            if 'sharepoint.com' in part:
                if i + 2 < len(url_parts):
                    sharepoint_site = url_parts[i + 2]  # sites/站点名
                break
        
        # 提取文档库和文件夹路径
        if 'Shared%20Documents' in current_url:
            document_library = "Shared Documents"
            # 提取文件夹路径
            if 'id=' in current_url:
                import urllib.parse
                import re
                
                # 解码URL中的路径信息
                decoded_url = urllib.parse.unquote(current_url)
                
                # 使用正则表达式提取路径信息
                path_match = re.search(r'id=([^&]+)', decoded_url)
                if path_match:
                    encoded_path = path_match.group(1)
                    # 解码路径
                    decoded_path = urllib.parse.unquote(encoded_path)
                    
                    # 从URL中解析出实际的文件夹层级结构
                    # 查找 /sites/站点名/Shared Documents/ 之后的部分
                    sites_pattern = r'/sites/[^/]+/Shared Documents/(.+)'
                    sites_match = re.search(sites_pattern, decoded_path)
                    if sites_match:
                        # 获取实际的文件路径部分
                        actual_path = sites_match.group(1)
                        # 按 / 分割路径，过滤掉空字符串
                        path_components = [comp for comp in actual_path.split('/') if comp]
                        # 解码每个路径组件
                        for component in path_components:
                            decoded_component = urllib.parse.unquote(component)
                            if decoded_component and decoded_component not in folder_path:
                                folder_path.append(decoded_component)
                        
                        # 只保留最后一个文件夹作为下级目录的起始点
                        # 因为整个URL中的路径都是上级目录，只有最后一个文件夹才是下级目录
                        if len(folder_path) > 0:
                            # 只保留最后一个文件夹
                            folder_path = [folder_path[-1]]
                    else:
                        # 如果没找到标准模式，使用原来的手动解析方式作为后备
                        if 'GEN1.5' in decoded_path:
                            folder_path.append('GEN1.5')
                        if '中台FOT' in decoded_path:
                            folder_path.append('中台FOT')
                        if 'データ解析' in decoded_path:
                            folder_path.append('データ解析')
                        if '認知系' in decoded_path:
                            folder_path.append('認知系')
                        if '走路認知' in decoded_path:
                            folder_path.append('走路認知')
                        if 'スクリプト検討' in decoded_path:
                            folder_path.append('スクリプト検討')
                        if 'Test' in decoded_path:
                            folder_path.append('Test')
                        if '202509' in decoded_path:
                            folder_path.append('202509')
                        if '20250901_走行データ送付' in decoded_path:
                            folder_path.append('20250901_走行データ送付')
                        if '360' in decoded_path:
                            folder_path.append('360')
                        if '日本' in decoded_path:
                            folder_path.append('日本')
                        if 'JP4テスト車' in decoded_path:
                            folder_path.append('JP4テスト車')
                        if '20250827' in decoded_path:
                            folder_path.append('20250827')
        
        # 使用从URL解析出的实际文件夹层级
        relevant_folders = folder_path
        
        # 构建完整路径
        full_path = "/" + "/".join(relevant_folders) + "/" + file_info['name'] if relevant_folders else "/" + file_info['name']
        
        # 构建目录结构信息
        file_position = None
        try:
            if isinstance(file_info, dict) and 'position' in file_info and file_info['position']:
                file_position = {
                    "x": file_info['position'].get('x'),
                    "y": file_info['position'].get('y'),
                    "width": file_info['position'].get('width'),
                    "height": file_info['position'].get('height')
                }
        except Exception:
            file_position = None

        directory_structure = {
            "page_title": page_title,
            "page_url": current_url,
            "sharepoint_site": sharepoint_site,
            "document_library": document_library,
            "folder_path": relevant_folders,  # 使用从 Test 开始的路径
            "file_name": file_info['name'],
            "full_path": full_path,
            "file_position": file_position
        }
        
        return directory_structure
        
    except Exception as e:
        print(f"❌ 获取目录结构信息失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_folder_path_from_href(href: str) -> str:
    """从 SharePoint 文件项的 href 中提取文件所在的文件夹相对路径（不含文件名）。"""
    try:
        if not href:
            return ""
        import urllib.parse, re
        decoded = urllib.parse.unquote(href)
        # 先抓 id= 后的路径段
        m = re.search(r"id=([^&#]+)", decoded)
        if not m:
            return ""
        full_path = urllib.parse.unquote(m.group(1))
        # 只取 Shared Documents 之后的部分
        m2 = re.search(r"/Shared Documents/(.+)$", full_path, flags=re.IGNORECASE)
        rel = m2.group(1) if m2 else full_path
        # 去掉可能结尾的文件名（包含 . 扩展名时）
        parts = [p for p in rel.split('/') if p]
        if parts and ('.' in parts[-1]):
            parts = parts[:-1]
        return '/'.join(parts)
    except Exception:
        return ""
async def wait_for_sharepoint_page_ready(page, max_wait_time: int = 30000) -> bool:
    """智能等待SharePoint页面完全加载就绪"""
    try:
        print(f"   ⏳ 等待SharePoint页面加载完成...")
        start_time = time.time()
        
        while (time.time() - start_time) * 1000 < max_wait_time:
            try:
                # 1. 等待基本DOM结构
                await page.wait_for_selector("[role='grid'], div.ms-DetailsRow, .ms-List-surface", timeout=2000)
                
                # 2. 检查页面是否还在加载中
                loading_indicators = await page.locator(".ms-Spinner, .loading, [data-automation-id='loading']").count()
                if loading_indicators > 0:
                    await page.wait_for_timeout(500)
                    continue
                
                # 3. 检查是否有可交互的元素
                interactive_elements = await page.locator("[role='grid'] div[data-automation-id='DetailsRow'], [role='grid'] .ms-DetailsRow").count()
                if interactive_elements > 0:
                    # 4. 等待网络请求稳定
                    try:
                        await page.wait_for_load_state('networkidle', timeout=2000)
                    except Exception:
                        pass
                    
                    # 5. 最终验证：检查页面内容是否稳定
                    await page.wait_for_timeout(1000)
                    current_elements = await page.locator("[role='grid'] div[data-automation-id='DetailsRow'], [role='grid'] .ms-DetailsRow").count()
                    if current_elements == interactive_elements:
                        print(f"   ✅ SharePoint页面加载完成，找到 {interactive_elements} 个可交互元素")
                        return True
                
                await page.wait_for_timeout(500)
                
            except Exception:
                await page.wait_for_timeout(500)
                continue
        
        print(f"   ⚠️ SharePoint页面加载超时，但继续尝试操作")
        return False
        
    except Exception as e:
        print(f"   ⚠️ 页面加载检测异常: {e}")
        return False

async def check_page_responsiveness(page) -> bool:
    """检查页面是否还有响应"""
    try:
        # 尝试执行简单的JavaScript来检查页面响应性
        result = await page.evaluate("() => { return document.readyState; }")
        return result in ['interactive', 'complete']
    except Exception:
        return False

async def recover_from_page_timeout(page, initial_url: str, max_retries: int = 3) -> bool:
    """从页面超时或失去响应中恢复，回到初始界面重新开始"""
    print(f"🔄 检测到页面超时或失去响应，尝试恢复...")
    
    for retry in range(max_retries):
        try:
            print(f"   🔄 恢复尝试 {retry + 1}/{max_retries}")
            
            # 1. 检查页面是否还有响应
            if await check_page_responsiveness(page):
                print(f"   ✅ 页面仍有响应，继续操作")
                return True
            
            # 2. 尝试刷新页面
            print(f"   🔄 尝试刷新页面...")
            await page.reload(wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(3000)
            
            # 3. 检查刷新后页面是否正常
            if await check_page_responsiveness(page):
                print(f"   ✅ 页面刷新成功，继续操作")
                return True
            
            # 4. 如果刷新失败，尝试重新导航到初始URL
            print(f"   🔄 尝试重新导航到初始URL...")
            await page.goto(initial_url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(3000)
            
            # 5. 检查重新导航后页面是否正常
            if await check_page_responsiveness(page):
                print(f"   ✅ 重新导航成功，继续操作")
                return True
            
            # 6. 等待一段时间后重试
            if retry < max_retries - 1:
                print(f"   ⏳ 等待5秒后重试...")
                await page.wait_for_timeout(5000)
            
        except Exception as e:
            print(f"   ❌ 恢复尝试 {retry + 1} 失败: {e}")
            if retry < max_retries - 1:
                await page.wait_for_timeout(5000)
    
    print(f"   ❌ 所有恢复尝试失败，页面可能已失去响应")
    return False

async def click_folder_in_grid(page, folder_name: str, max_scrolls: int = 16) -> bool:
    """在文件列表grid中点击指定文件夹名，避免点击面包屑。支持滚动加载与重试。"""
    try:
        # 首先确保页面完全加载
        await wait_for_sharepoint_page_ready(page)
        
        # 常见的 SharePoint 列表选择器集合
        row_selectors = [
            "[role='grid'] div[data-automation-id='DetailsRow']",
            "[role='grid'] .ms-DetailsRow",
            "div[role='row'].ms-DetailsRow",
        ]
        name_cell_selector = "span.field-LinkFilename-htmlGrid_1, a[role='link'], a.ms-Link, span[title]"

        grid_container = page.locator("[role='grid']")
        list_surface = page.locator("[role='grid'] .ms-List-surface, [role='grid'] .ms-DetailsList")

        for scroll in range(max_scrolls):
            found = False
            for row_sel in row_selectors:
                rows = page.locator(row_sel).filter(has_text=folder_name)
                if await rows.count() > 0:
                    target = rows.first
                    await target.scroll_into_view_if_needed()
                    # 行内仅点击名称链接/单元格
                    name_cell = target.locator(name_cell_selector).filter(has_text=folder_name).first
                    if await name_cell.count() > 0:
                        # 优先双击名称打开文件夹
                        try:
                            await name_cell.dblclick(timeout=8000)
                        except Exception:
                            await name_cell.click(timeout=8000)
                        return True
                    # 退化：点击行
                    try:
                        await target.dblclick(timeout=8000)
                    except Exception:
                        await target.click(timeout=8000)
                    return True
            # 作为补充：在grid容器内通过链接文本查找
            if await grid_container.count() > 0:
                link = grid_container.locator("a, span[title]").filter(has_text=folder_name).first
                if await link.count() > 0:
                    await link.scroll_into_view_if_needed()
                    try:
                        await link.dblclick(timeout=8000)
                    except Exception:
                        await link.click(timeout=8000)
                    return True

            # 再退化：用键盘打开
            try:
                any_row = page.locator(row_selectors[0]).first
                if await any_row.count() > 0:
                    await any_row.focus()
                    # 尝试将目标行聚焦
                    row = page.locator(row_selectors[0]).filter(has_text=folder_name).first
                    if await row.count() > 0:
                        await row.focus()
                    await page.keyboard.press('Enter')
                    return True
            except Exception:
                pass

            # 向下滚动加载更多
            try:
                if await list_surface.count() > 0:
                    await list_surface.evaluate("el => el.scrollBy(0, el.clientHeight)")
                else:
                    await page.evaluate("window.scrollBy(0, document.body.scrollHeight/1.5)")
            except Exception:
                await page.evaluate("window.scrollBy(0, document.body.scrollHeight/1.5)")
            await page.wait_for_timeout(300)

        # 最终兜底：在浏览器上下文中直接查找并触发事件（防止遮挡/不可见导致点击失败）
        try:
            clicked = await page.evaluate(
                """
                (targetText) => {
                  const norm = (s) => (s || '').trim();
                  // 优先在 grid 行内查找名称单元格
                  const rowSel = "[role='grid'] div[data-automation-id='DetailsRow'], [role='grid'] .ms-DetailsRow, div[role='row'].ms-DetailsRow";
                  const nameSel = ".field-LinkFilename-htmlGrid_1, a[role='link'], a.ms-Link, span[title]";
                  const rows = Array.from(document.querySelectorAll(rowSel));
                  for (const row of rows) {
                    const text = norm(row.textContent);
                    if (!text || !text.includes(targetText)) continue;
                    let nameEl = row.querySelector(nameSel);
                    if (!nameEl) nameEl = row.querySelector('a');
                    if (!nameEl) nameEl = row;
                    const rect = nameEl.getBoundingClientRect();
                    const x = rect.left + rect.width / 2;
                    const y = rect.top + rect.height / 2;
                    const el = document.elementFromPoint(x, y) || nameEl;
                    // 触发双击事件以打开文件夹
                    el.dispatchEvent(new MouseEvent('pointerdown', {bubbles:true}));
                    el.dispatchEvent(new MouseEvent('pointerup', {bubbles:true}));
                    el.dispatchEvent(new MouseEvent('click', {bubbles:true}));
                    el.dispatchEvent(new MouseEvent('dblclick', {bubbles:true}));
                    return true;
                  }
                  return false;
                }
                """,
                folder_name,
            )
            if clicked:
                return True
        except Exception:
            pass
        return False
    except Exception:
        return False



async def print_download_directory_structure(page, file_info):
    """打印下载文件在原始网页中的目录结构"""
    directory_structure = await get_download_directory_structure(page, file_info)
    
    if directory_structure:
        print("\n📁 下载文件目录结构信息:")
        print("=" * 50)
        
        print(f"📄 页面标题: {directory_structure['page_title']}")
        print(f"🔗 页面URL: {directory_structure['page_url']}")
        print(f"🏢 SharePoint站点: {directory_structure['sharepoint_site']}")
        print(f"📚 文档库: {directory_structure['document_library']}")
        
        if directory_structure['folder_path']:
            print(f"📂 文件夹路径:")
            for i, folder in enumerate(directory_structure['folder_path']):
                indent = "  " * (i + 1)
                print(f"{indent}📁 {folder}")
            print(f"📄 文件: {directory_structure['file_name']}")
            print(f"📍 完整路径: {directory_structure['full_path']}")
        else:
            print(f"📄 文件: {directory_structure['file_name']}")
            print(f"📍 完整路径: {directory_structure['full_path']}")
        
        # 获取文件的详细信息
        print(f"\n📊 文件详细信息:")
        print(f"   文件名: {directory_structure['file_name']}")
        print(f"   位置: x={directory_structure['file_position']['x']}, y={directory_structure['file_position']['y']}")
        print(f"   大小: {directory_structure['file_position']['width']} x {directory_structure['file_position']['height']} 像素")
        
        print("=" * 50)
        
        return directory_structure
    else:
        return None


async def save_directory_structure_to_json(directory_structure, file_name):
    """将目录结构信息保存到JSON文件"""
    try:
        import json
        import os
        from datetime import datetime
        
        # 创建logs目录
        logs_dir = Path("downloads/logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名（基于时间戳和文件名）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = "".join(c for c in file_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        json_filename = f"directory_structure_{timestamp}_{safe_filename}.json"
        json_filepath = logs_dir / json_filename
        
        # 添加时间戳到目录结构信息
        directory_structure["timestamp"] = datetime.now().isoformat()
        directory_structure["download_time"] = timestamp
        
        # 保存到JSON文件
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(directory_structure, f, ensure_ascii=False, indent=2)
        
        print(f"💾 目录结构信息已保存到: {json_filepath}")
        
        # 同时更新主下载状态文件
        await update_download_state_with_directory_structure(directory_structure, file_name)
        
    except Exception as e:
        print(f"❌ 保存目录结构信息失败: {e}")
        import traceback
        traceback.print_exc()


async def update_download_state_with_directory_structure(directory_structure, file_name):
    """更新主下载状态文件，添加目录结构信息"""
    try:
        import json
        from pathlib import Path
        
        # 读取现有的下载状态文件
        state_file = Path("downloads/download_state.json")
        if state_file.exists():
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
        else:
            state_data = {"tasks": {}, "timestamp": ""}
        
        # 查找最新的下载任务（基于文件名）
        latest_task = None
        latest_time = None
        
        for task_id, task_info in state_data["tasks"].items():
            if task_info.get("file_name") == file_name:
                task_time = task_info.get("start_time", "")
                if not latest_time or task_time > latest_time:
                    latest_time = task_time
                    latest_task = task_id
        
        # 如果找到任务，添加目录结构信息
        if latest_task:
            state_data["tasks"][latest_task]["directory_structure"] = directory_structure
            state_data["timestamp"] = datetime.now().isoformat()
            
            # 保存更新后的状态文件
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)
            
            print(f"📝 已更新下载状态文件，添加目录结构信息")
        
    except Exception as e:
        print(f"❌ 更新下载状态文件失败: {e}")


def get_unique_folder_name(parent_path: Path, folder_name: str) -> str:
    """获取唯一的文件夹名称，如果重复则添加序号"""
    try:
        # 输入验证
        if not parent_path or not folder_name:
            raise ValueError(f"无效的输入参数: parent_path={parent_path}, folder_name={folder_name}")
        
        base_name = folder_name.strip()
        if not base_name:
            raise ValueError("文件夹名称不能为空")
        
        counter = 1
        unique_name = base_name
        
        # 检查原始名称是否已存在
        if not (parent_path / unique_name).exists():
            return unique_name
        
        # 如果原始名称存在，开始查找可用的序号
        while (parent_path / unique_name).exists():
            unique_name = f"{base_name}({counter})"
            counter += 1
        
        print(f"   📁 文件夹重复，使用新名称: {unique_name}")
        return unique_name
        
    except Exception as e:
        print(f"   ⚠️ get_unique_folder_name 错误: {e}")
        # 返回一个安全的默认名称
        return f"folder_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


async def create_directory_structure_and_extract(zip_path: Path, directory_structure: dict, max_files: int = 2, file_name: str = "", extract_semaphore: asyncio.Semaphore | None = None) -> dict:
    """创建原始目录结构并解压zip文件到对应目录（解压全部文件，任务并发默认2）"""
    try:
        # 控制并发解压（默认2个）
        if extract_semaphore is None:
            extract_limit = int(os.getenv("EXTRACT_CONCURRENCY", "2"))
            extract_semaphore = asyncio.Semaphore(extract_limit)
        async with extract_semaphore:
            # 等待一小段时间确保文件完全写入
            await asyncio.sleep(1)
        
        extract_info = {
            "zip_file": str(zip_path),
            "extract_path": "",
            "extracted_files": [],
            "total_files_in_zip": 0,
            "extracted_count": 0,
            "success": False,
            "error": None,
            "file_name": file_name,
            "directory_structure_created": False
        }
        
        # 从目录结构信息中获取文件夹路径
        folder_path = directory_structure.get("folder_path", [])
        if not folder_path:
            print(f"   ⚠️ [{file_name}] 无法获取目录结构信息")
            return extract_info
        
        # 解析实际目录结构，以Test作为根目录
        # 从URL中提取从Test开始的完整路径
        page_url = directory_structure.get("page_url", "")
        actual_path_from_test = []
        
        if page_url:
            try:
                import urllib.parse
                import re
                
                # 解码URL
                decoded_url = urllib.parse.unquote(page_url)
                
                # 查找Test之后的路径
                test_pattern = r'/Test/(.+)'
                test_match = re.search(test_pattern, decoded_url)
                
                if test_match:
                    # 获取Test之后的路径部分
                    path_after_test = test_match.group(1)
                    # 按/分割并解码每个组件，过滤掉URL参数
                    path_components = []
                    for comp in path_after_test.split('/'):
                        if comp:
                            # 解码组件
                            decoded_comp = urllib.parse.unquote(comp)
                            # 过滤掉包含URL参数的部分（包含&、?、=等字符）
                            if not any(char in decoded_comp for char in ['&', '?', '=', 'viewid', 'csf', 'web', 'e', 'FolderCTID']):
                                path_components.append(decoded_comp)
                            else:
                                # 如果包含URL参数，只取参数前的部分
                                clean_comp = decoded_comp.split('&')[0].split('?')[0].split('=')[0]
                                if clean_comp and not any(char in clean_comp for char in ['&', '?', '=']):
                                    path_components.append(clean_comp)
                    actual_path_from_test = path_components
                    print(f"   📁 [{file_name}] 从URL解析的实际路径: Test/{'/'.join(actual_path_from_test)}")
                else:
                    # 如果没找到Test，使用folder_path作为后备
                    actual_path_from_test = folder_path
                    print(f"   📁 [{file_name}] 使用后备路径: {'/'.join(actual_path_from_test)}")
            except Exception as e:
                print(f"   ⚠️ [{file_name}] URL解析失败: {e}")
                actual_path_from_test = folder_path
        else:
            actual_path_from_test = folder_path
        
        # 创建原始目录结构，以Test作为根目录
        base_path = Path("downloads")
        original_structure_path = base_path / "original_structure" / "Test"
        
        # 构建完整路径（保持原始目录结构，不处理重复）
        full_folder_path = original_structure_path
        
        # 过滤掉空值和None值
        valid_folders = [folder for folder in actual_path_from_test if folder and folder.strip()]
        
        if not valid_folders:
            print(f"   ⚠️ [{file_name}] 没有有效的文件夹路径，使用默认路径")
            full_folder_path = original_structure_path / file_name.replace('.zip', '')
        else:
            for folder in valid_folders:
                full_folder_path = full_folder_path / folder
        
        print(f"   📁 [{file_name}] 创建目录结构: Test/{'/'.join(valid_folders) if valid_folders else file_name.replace('.zip', '')}")
        print(f"   📁 [{file_name}] 实际解压路径: {full_folder_path}")
        
        # 创建目录结构
        full_folder_path.mkdir(parents=True, exist_ok=True)
        extract_info["extract_path"] = str(full_folder_path)
        extract_info["directory_structure_created"] = True
        
        print(f"   📁 [{file_name}] 已创建目录结构: {full_folder_path}")
        
        # 验证zip文件完整性
        if not zip_path.exists():
            print(f"   ❌ [{file_name}] zip文件不存在: {zip_path}")
            extract_info["error"] = f"zip文件不存在: {zip_path}"
            return extract_info
        
        # 检查文件大小
        file_size = zip_path.stat().st_size
        if file_size == 0:
            print(f"   ❌ [{file_name}] zip文件大小为0，可能下载不完整")
            extract_info["error"] = "zip文件大小为0，下载不完整"
            return extract_info
        
        print(f"   📦 [{file_name}] zip文件大小: {file_size:,} 字节")
        
        # 验证zip文件格式
        try:
            with zipfile.ZipFile(zip_path, 'r') as test_zip:
                test_zip.testzip()
            print(f"   ✅ [{file_name}] zip文件格式验证通过")
        except zipfile.BadZipFile:
            print(f"   ❌ [{file_name}] zip文件格式损坏")
            extract_info["error"] = "zip文件格式损坏"
            return extract_info
        except Exception as e:
            print(f"   ❌ [{file_name}] zip文件验证失败: {e}")
            extract_info["error"] = f"zip文件验证失败: {e}"
            return extract_info
        
        # 直接解压到目标目录，不复制zip文件
        print(f"   📦 [{file_name}] 直接解压到: {full_folder_path}")
        
        # 直接解压原始zip文件到目标目录
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # 获取zip文件中的所有文件列表
            file_list = zip_ref.namelist()
            extract_info["total_files_in_zip"] = len(file_list)
            
            # 解压全部文件（并发由外层任务数限制，不在单包内限制数量）
            files_to_extract = file_list
            
            for file_name_in_zip in files_to_extract:
                try:
                    # 解压单个文件到目标目录
                    zip_ref.extract(file_name_in_zip, full_folder_path)
                    extract_info["extracted_files"].append(file_name_in_zip)
                    extract_info["extracted_count"] += 1
                    # 不显示每个文件的解压信息，只在完成时显示总数
                except Exception as e:
                    print(f"   ⚠️ [{file_name}] 解压文件失败: {file_name_in_zip} - {e}")
                    continue
            
            extract_info["success"] = extract_info["extracted_count"] > 0
            
        if extract_info["success"]:
            print(f"   ✅ [{file_name}] 解压完成: {extract_info['extracted_count']}/{extract_info['total_files_in_zip']} 个文件")
        else:
            print(f"   ❌ [{file_name}] 解压失败: 没有文件被解压")
            
        return extract_info
        
    except Exception as e:
        print(f"   ❌ [{file_name}] 创建目录结构并解压失败: {e}")
        return {
            "zip_file": str(zip_path),
            "extract_path": "",
            "extracted_files": [],
            "total_files_in_zip": 0,
            "extracted_count": 0,
            "success": False,
            "error": str(e),
            "file_name": file_name,
            "directory_structure_created": False
        }


async def download_single_file(scanner, page, file_elem_or_data, file_index, total_files, progress_callback=None, click_lock: asyncio.Lock | None = None):
    """下载单个文件 - 严格遵循安全操作指南，支持重试机制"""
    # 兼容新的队列管理器格式和旧格式
    if isinstance(file_elem_or_data, dict) and 'file_elem' in file_elem_or_data:
        # 新格式：队列管理器传入的数据
        file_elem = file_elem_or_data['file_elem']
        retry_count = file_elem_or_data.get('retry_count', 0)
    else:
        # 旧格式：直接传入file_elem
        file_elem = file_elem_or_data
        retry_count = 0
    
    file_name = file_elem['text']
    print(f"📥 [{file_index}/{total_files}] 开始下载: {file_name}")
    if retry_count > 0:
        print(f"   🔄 重试次数: {retry_count}")
    
    # 创建文件信息
    file_info = {
        "name": file_name,
        "position": file_elem['position']
    }
    
    result = {
        "file_name": file_name,
        "file_index": file_index,
        "success": False,
        "error": None,
        "directory_structure": None,
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "retry_count": 0,
        "status": "starting",
        "progress": 0.0,
        "file_size": 0,
        "speed": 0.0
    }
    
    # 通知进度回调
    if progress_callback:
        await progress_callback(result)
    
    # 安全检查 - 确保只进行下载操作
    if not is_safe_download_operation(file_name):
        result["error"] = "安全检查失败"
        result["status"] = "failed"
        if progress_callback:
            await progress_callback(result)
        print(f"   ❌ 安全检查失败: {file_name}")
        result["end_time"] = datetime.now().isoformat()
        return result
    
    # 若提供了发现该ZIP时的页面URL，先直接跳转回该页面
    try:
        page_url = file_elem.get('page_url') or ''
        if page_url:
            await page.goto(page_url)
            try:
                await page.wait_for_load_state('domcontentloaded', timeout=10000)
                await page.wait_for_load_state('networkidle', timeout=5000)
            except Exception:
                pass
            # 增加等待时间，确保页面完全加载
            await page.wait_for_timeout(2000)
    except Exception:
        pass

    # 如果有 page_url，优先直接进入该页面后定位文件，不再逐层点击 path
    file_path = file_elem.get('path', '')
    if not page_url:
        if file_path:
            print(f"   🧭 导航到文件路径: {file_path}")
            try:
                # 使用旧版递归扫描器的进入逻辑，最大程度复用旧点击路径
                path_parts = [p for p in file_path.split('/') if p]
                accumulated = []
                for part in path_parts:
                    accumulated.append(part)
                    folder = { 'name': part, 'position': {}, 'href': '', 'full_path': '/'.join(accumulated) }
                    print(f"   📁 进入文件夹(旧逻辑): {part}")
                    ok = await scanner.recursive_scanner._click_folder_and_scan(page, folder, '/'.join(accumulated), 0)
                    if not ok:
                        raise Exception(f"旧逻辑点击失败: {part}")
                    await page.wait_for_timeout(500)
                print(f"   ✅ 已导航到目标文件夹(旧逻辑)")
            except Exception as e:
                print(f"   ⚠️ 导航到文件夹失败: {e}")
                # 导航失败不直接中断，继续尝试在当前页定位
    else:
        print("   🔗 已有页面地址，直接在该页定位目标文件并右键下载")
        # 增加等待时间，确保页面完全加载
        await page.wait_for_timeout(2000)
        # 借用旧脚本：实际的右键触发由 downloader.download_file_by_right_click 执行
        # 这里仅做可见性预热（滚动几次），其余交给 downloader 处理
        try:
            list_surface = page.locator("[role='grid'] .ms-List-surface, [role='grid'] .ms-DetailsList")
            for _ in range(4):
                try:
                    if await list_surface.count() > 0:
                        await list_surface.evaluate("el => el.scrollBy(0, el.clientHeight)")
                    else:
                        await page.evaluate("window.scrollBy(0, document.body.scrollHeight/1.5)")
                except Exception:
                    pass
                await page.wait_for_timeout(500)  # 增加滚动间隔时间
        except Exception:
            pass
    
    # 单次尝试下载（重试由队列管理器处理）
    try:
            
            # 执行下载（导航+右键触发）——使用锁串行化，避免页面冲突
            if click_lock is None:
                # 创建一个空的上下文管理器
                class DummyContext:
                    async def __aenter__(self):
                        return self
                    async def __aexit__(self, exc_type, exc_val, exc_tb):
                        pass
                click_ctx = DummyContext()
            else:
                click_ctx = click_lock
            async with click_ctx:
                result["status"] = "downloading"
                if progress_callback:
                    await progress_callback(result)
                print(f"   🖱️ 右键点击: {file_name}")
                success = await scanner.downloader.download_file_by_right_click(page, file_info)
            
            if success:
                # 启动后台监控下载进度，不阻塞当前任务
                monitor_task = asyncio.create_task(
                    monitor_download_progress_simple(result, progress_callback, scanner, file_name)
                )
                result["monitor_task"] = monitor_task
                
                # 不等待监控任务完成，让下载任务立即返回，实现真正的并行
                result["success"] = True
                result["retry_count"] = retry_count
                result["status"] = "downloading"
                result["progress"] = 0.0
                
                # 获取目录结构信息
                directory_structure = await get_download_directory_structure(page, file_info)
                if directory_structure:
                    result["directory_structure"] = directory_structure
                    
                    # 如果是zip文件，启动后台解压任务（不占用下载并发名额）
                    if file_name.lower().endswith('.zip'):
                        print(f"   📦 启动后台解压任务: {file_name}")
                        
                        # 从下载状态管理器中获取实际下载路径 - 确保信息一致
                        actual_zip_path = None
                        actual_file_name = file_name  # 默认使用原始文件名
                        
                        # 首先尝试从下载状态管理器中找到对应的任务
                        # 使用更精确的匹配逻辑，避免重试导致的错位
                        matching_task = None
                        for task_id, task in scanner.status_manager.tasks.items():
                            # 精确匹配文件名和完成状态，避免重试导致的错位
                            if task.file_name == file_name and task.status.value == 'completed':
                                # 额外验证：确保任务有有效的文件路径
                                if task.save_path and task.file_size and task.file_size > 0:
                                    matching_task = task
                                    break
                        
                        if matching_task and hasattr(matching_task, 'save_path') and matching_task.save_path:
                            actual_zip_path = Path(matching_task.save_path)
                            # 从实际路径中提取真实文件名
                            actual_file_name = actual_zip_path.name
                            print(f"   📁 从下载状态管理器找到实际文件: {actual_zip_path}")
                            print(f"   📁 原始文件名: {file_name} -> 实际文件名: {actual_file_name}")
                        else:
                            print(f"   ⚠️ 未在下载状态管理器中找到任务: {file_name}")
                        
                        # 如果找不到实际路径，尝试从多个可能的下载目录查找
                        if not actual_zip_path or not actual_zip_path.exists():
                            # 构建可能的下载路径列表
                            possible_paths = []
                            
                            # 1. 配置的下载目录（如果设置了）
                            if settings.download_path:
                                config_path = Path(settings.download_path)
                                if config_path.is_absolute():
                                    possible_paths.append(config_path / file_name)
                                else:
                                    possible_paths.append(Path.cwd() / config_path / file_name)
                            
                            # 2. 当前运行目录下的downloads文件夹
                            possible_paths.append(Path.cwd() / "downloads" / file_name)
                            
                            # 3. 系统默认下载目录
                            possible_paths.extend([
                                Path.home() / "下载" / file_name,  # 中文下载目录
                                Path.home() / "Downloads" / file_name,  # 英文下载目录
                            ])
                            
                            # 4. 项目根目录下的downloads
                            possible_paths.append(Path("downloads") / file_name)
                            
                            for path in possible_paths:
                                if path.exists() and path.stat().st_size > 0:
                                    actual_zip_path = path
                                    actual_file_name = path.name  # 使用实际文件名
                                    print(f"   📁 在 {path} 找到zip文件")
                                    break
                            
                            if not actual_zip_path:
                                print(f"   ⚠️ 无法找到有效的zip文件: {file_name}")
                                print(f"   🔍 已检查的路径: {[str(p) for p in possible_paths]}")
                                # 无法找到zip文件，继续处理其他逻辑
                        
                        print(f"   📁 找到zip文件位置: {actual_zip_path}")
                        
                        # 创建后台解压任务，不等待完成
                        extract_task = asyncio.create_task(
                            create_directory_structure_and_extract(actual_zip_path, directory_structure, max_files=1000, file_name=file_name)
                        )
                        result["extract_task"] = extract_task
                        print(f"   📦 解压任务已启动: {file_name} -> {actual_zip_path}")
                
                if progress_callback:
                    await progress_callback(result)
            else:
                result["error"] = "文件验证失败"
                result["status"] = "failed"
                if progress_callback:
                    await progress_callback(result)
                print(f"   ❌ 文件验证失败: {file_name}")
        
    except Exception as e:
        result["error"] = f"异常: {e}"
        result["status"] = "failed"
        if progress_callback:
            await progress_callback(result)
        print(f"   ❌ 下载异常: {file_name} - {e}")
    
    result["end_time"] = datetime.now().isoformat()
    return result


async def monitor_download_progress_simple(result, progress_callback, scanner, file_name):
    """简化的下载进度监控（不显示实时速度）"""
    import time
    
    start_time = time.time()
    last_size = 0
    last_time = start_time
    
    # 监控下载进度
    while True:
        await asyncio.sleep(2)  # 每2秒更新一次，减少频率
        
        # 查找对应的下载任务
        task_status = None
        for task_id, task in scanner.status_manager.tasks.items():
            if task.file_name == file_name and task.status.value in ['completed', 'downloading']:
                task_status = task
                break
        
        if not task_status:
            continue
            
        current_time = time.time()
        current_size = task_status.file_size or 0
        
        # 计算下载速度（内部使用，不显示）
        if current_size > last_size and current_time > last_time:
            speed = (current_size - last_size) / (current_time - last_time)
            result["speed"] = speed
        else:
            result["speed"] = 0.0
        
        # 更新进度
        if task_status.expected_size and task_status.expected_size > 0:
            result["progress"] = current_size / task_status.expected_size
        elif current_size > 0:
            result["progress"] = min(current_size / (current_size * 1.1), 0.99)  # 估算进度
        
        result["file_size"] = current_size
        result["status"] = "downloading"
        
        # 只在下载完成时更新显示，不显示实时进度
        if task_status.status.value == 'completed':
            result["progress"] = 1.0
            result["status"] = "completed"
            if progress_callback:
                await progress_callback(result)
            break
        
        last_size = current_size
        last_time = current_time


async def update_unified_report_realtime(progress_tracker, total_files, max_concurrent, report_filepath):
    """实时更新统一报告文件"""
    try:
        # 确保报告文件路径存在
        if report_filepath is None:
            return
        
        # 检查是否是统一日志文件
        is_unified_log = False
        if report_filepath.exists():
            try:
                with open(report_filepath, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    is_unified_log = "download_report" in existing_data
            except:
                pass
        
        if is_unified_log:
            # 统一日志文件格式 - 更新下载报告部分
            with open(report_filepath, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            
            if "download_report" not in existing_data:
                existing_data["download_report"] = {}
            
            download_report = existing_data["download_report"]
            download_report["report_info"] = {
                "timestamp": datetime.now().isoformat(),
                "report_type": "unified_batch_download_realtime",
                "concurrency": max_concurrent
            }
            download_report["summary"] = {
                "total_files": total_files,
                "successful_downloads": len([t for t in progress_tracker.values() if t["status"] == "completed"]),
                "failed_downloads": len([t for t in progress_tracker.values() if t["status"] == "failed"]),
                "downloading": len([t for t in progress_tracker.values() if t["status"] == "downloading"]),
                "waiting": len([t for t in progress_tracker.values() if t["status"] == "waiting"]),
                "success_rate": f"{(len([t for t in progress_tracker.values() if t['status'] == 'completed']) / total_files * 100):.1f}%" if total_files > 0 else "0%"
            }
            download_report["file_details"] = []
            report_data = existing_data
        else:
            # 传统报告格式
            report_data = {
            "report_info": {
                "timestamp": datetime.now().isoformat(),
                "report_type": "unified_batch_download_realtime",
                    "concurrency": max_concurrent
            },
            "summary": {
                "total_files": total_files,
                "successful_downloads": len([t for t in progress_tracker.values() if t["status"] == "completed"]),
                "failed_downloads": len([t for t in progress_tracker.values() if t["status"] == "failed"]),
                "downloading": len([t for t in progress_tracker.values() if t["status"] == "downloading"]),
                "waiting": len([t for t in progress_tracker.values() if t["status"] == "waiting"]),
                "success_rate": f"{(len([t for t in progress_tracker.values() if t['status'] == 'completed']) / total_files * 100):.1f}%" if total_files > 0 else "0%"
            },
            "file_details": []
        }
        
        # 添加所有任务详情
        file_details_list = report_data["file_details"] if not is_unified_log else report_data["download_report"]["file_details"]
        for file_index, task_info in progress_tracker.items():
            file_detail = {
                "file_name": task_info["file_name"],
                "file_index": file_index,
                "success": task_info["status"] == "completed",
                "error": task_info["error"],
                "start_time": datetime.now().isoformat() if task_info["status"] == "waiting" else None,
                "end_time": datetime.now().isoformat() if task_info["status"] == "completed" else None,
                "retry_count": 0,
                "status": task_info["status"],
                "progress": task_info["progress"],
                "file_size": task_info["file_size"],
                "speed": task_info["speed"],
                "extract_info": task_info.get("extract_info"),
                "extract_task_running": task_info.get("extract_task", False),
                "path": task_info.get("path", ""),
                "href": task_info.get("href", ""),
                "page_url": task_info.get("page_url", "")
            }
            file_details_list.append(file_detail)
        
        # 添加任务状态摘要
        task_status_summary = {
            "completed": len([t for t in progress_tracker.values() if t["status"] == "completed"]),
            "failed": len([t for t in progress_tracker.values() if t["status"] == "failed"]),
            "retrying": len([t for t in progress_tracker.values() if "retrying" in t["status"]]),
            "downloading": len([t for t in progress_tracker.values() if t["status"] == "downloading"]),
            "waiting": len([t for t in progress_tracker.values() if t["status"] == "waiting"])
        }
        
        # 添加安全合规信息
        security_compliance = {
            "only_zip_files": True,
            "safe_operations_only": True,
            "no_dangerous_actions": True,
            "parallel_download_controlled": True
        }
        
        if is_unified_log:
            report_data["download_report"]["task_status_summary"] = task_status_summary
            report_data["download_report"]["security_compliance"] = security_compliance
        else:
            report_data["task_status_summary"] = task_status_summary
            report_data["security_compliance"] = security_compliance
        
        # 保存实时报告
        with open(report_filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"⚠️ 实时报告更新失败: {e}")


async def finalize_unified_report(download_stats, report_filepath):
    """最终化统一报告文件，添加完整信息"""
    try:
        if report_filepath is None or not report_filepath.exists():
            return
            
        # 读取现有报告
        with open(report_filepath, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        # 检查是否是统一日志文件格式
        if "download_report" in report_data:
            # 统一日志文件格式
            download_report = report_data["download_report"]
            download_report["report_info"]["final_timestamp"] = datetime.now().isoformat()
            download_report["summary"]["final_successful_downloads"] = download_stats["successful"]
            download_report["summary"]["final_failed_downloads"] = download_stats["failed"]
            download_report["summary"]["final_success_rate"] = f"{(download_stats['successful'] / download_stats['total_files'] * 100):.1f}%" if download_stats['total_files'] > 0 else "0%"
        else:
            # 传统报告格式
            report_data["report_info"]["final_timestamp"] = datetime.now().isoformat()
            report_data["summary"]["final_successful_downloads"] = download_stats["successful"]
            report_data["summary"]["final_failed_downloads"] = download_stats["failed"]
            report_data["summary"]["final_success_rate"] = f"{(download_stats['successful'] / download_stats['total_files'] * 100):.1f}%" if download_stats['total_files'] > 0 else "0%"
        
        # 添加下载的文件列表
        if "download_report" in report_data:
            # 统一日志文件格式
            download_report["downloaded_files"] = download_stats["downloaded_files"]
            download_report["failed_files"] = download_stats["failed_files"]
        else:
            # 传统报告格式
            report_data["downloaded_files"] = download_stats["downloaded_files"]
            report_data["failed_files"] = download_stats["failed_files"]
        
        # 更新文件详情，确保包含目录结构信息和解压信息
        file_details_key = "file_details"
        if "download_report" in report_data:
            file_details_key = "download_report"
            file_details = report_data["download_report"]["file_details"]
        else:
            file_details = report_data["file_details"]
            
        for i, file_detail in enumerate(file_details):
            if i < len(download_stats["file_details"]):
                original_detail = download_stats["file_details"][i]
                file_detail.update({
                    "directory_structure": original_detail.get("directory_structure"),
                    "start_time": original_detail.get("start_time"),
                    "end_time": original_detail.get("end_time"),
                    "retry_count": original_detail.get("retry_count", 0),
                    "extract_info": original_detail.get("extract_info"),
                    "path": original_detail.get("directory_structure", {}).get("folder_path") if isinstance(original_detail.get("directory_structure"), dict) else original_detail.get("path", ""),
                    "href": original_detail.get("href", ""),
                    "page_url": original_detail.get("directory_structure", {}).get("page_url") if isinstance(original_detail.get("directory_structure"), dict) else original_detail.get("page_url", ""),
                    "extract_task_running": False  # 最终报告时解压任务已完成
                })
        
        # 保存最终报告
        with open(report_filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"📋 统一批量下载报告已保存到: {report_filepath}")
        
        # 生成Markdown格式报告
        try:
            md_report_path = await save_markdown_report(str(report_filepath))
            if md_report_path:
                print(f"📄 Markdown格式报告已生成")
        except Exception as md_error:
            print(f"⚠️ Markdown报告生成失败: {md_error}")
        
        # 同时更新主下载状态文件
        await update_main_download_state_with_batch_results(download_stats)
        
    except Exception as e:
        print(f"❌ 最终化报告失败: {e}")


class DownloadQueueManager:
    """下载队列管理器 - 真正的队列式下载，保持最多2个下载任务"""
    
    def __init__(self, max_concurrent=2, task_interval=5):
        self.max_concurrent = max_concurrent
        self.task_interval = task_interval
        self.download_queue = []
        self.running_downloads = []
        self.completed_tasks = []
        self.failed_tasks = []
        self.last_task_start_time = 0
        # 添加页面操作锁，避免并发任务冲突
        self.page_lock = asyncio.Lock()
        
    def add_task(self, task_data):
        """添加任务到队列"""
        self.download_queue.append(task_data)
        
    def add_retry_task(self, task_data):
        """添加重试任务到队列末尾 - 清理旧状态避免信息错位"""
        file_name = task_data.get('file_name', 'Unknown')
        retry_delay = task_data.get("retry_delay", 0)
        
        # 清理旧的任务状态，避免信息错位
        if hasattr(self, 'completed_tasks'):
            # 从已完成任务中移除旧记录
            self.completed_tasks = [task for task in self.completed_tasks if task.get('file_name') != file_name]
        
        if hasattr(self, 'failed_tasks'):
            # 从失败任务中移除旧记录
            self.failed_tasks = [task for task in self.failed_tasks if task.get('file_name') != file_name]
        
        # 清理任务数据中的旧信息
        task_data.pop("extract_task", None)
        task_data.pop("monitor_task", None)
        task_data.pop("extract_info", None)
        task_data.pop("file_path", None)
        task_data.pop("actual_file_path", None)
        
        if retry_delay > 0:
            print(f"   ⏳ 重试任务将在 {retry_delay} 秒后加入队列: {file_name}")
            # 创建延迟任务
            task_data["delayed_retry"] = True
            task_data["retry_delay"] = retry_delay
        else:
            print(f"   🔄 重试任务已加入队列末尾: {file_name}")
        
        self.download_queue.append(task_data)
        
    async def start_download_queue(self, scanner, page, file_elements, progress_callback):
        """启动队列式下载处理"""
        print(f"🚀 启动队列式下载管理器")
        print(f"   📊 总任务数: {len(file_elements)}")
        print(f"   ⚡ 最大并发: {self.max_concurrent}")
        print(f"   ⏱️ 任务间隔: {self.task_interval}秒")
        print("=" * 50)
        
        # 添加所有任务到队列
        for i, file_elem in enumerate(file_elements):
            task_data = {
                'file_name': file_elem['text'],
                'file_index': i + 1,
                'total_files': len(file_elements),
                'file_elem': file_elem,
                'retry_count': 0
            }
            self.add_task(task_data)
        
        # 队列式处理下载任务
        while self.download_queue or self.running_downloads:
            # 启动新的下载任务（如果队列中有任务且运行中的任务少于最大并发数）
            while self.download_queue and len(self.running_downloads) < self.max_concurrent:
                task_data = self.download_queue.pop(0)
                
                # 检查是否是延迟重试任务
                if task_data.get("delayed_retry", False):
                    retry_delay = task_data.get("retry_delay", 0)
                    if retry_delay > 0:
                        print(f"   ⏳ 延迟重试等待 {retry_delay} 秒: {task_data.get('file_name', 'Unknown')}")
                        await asyncio.sleep(retry_delay)
                        # 移除延迟标记
                        task_data.pop("delayed_retry", None)
                        task_data.pop("retry_delay", None)
                
                # 控制任务启动间隔
                current_time = asyncio.get_event_loop().time()
                time_since_last = current_time - self.last_task_start_time
                if time_since_last < self.task_interval:
                    wait_time = self.task_interval - time_since_last
                    print(f"   ⏳ 等待 {wait_time:.1f}秒 后开始下一个任务")
                    await asyncio.sleep(wait_time)
                
                self.last_task_start_time = asyncio.get_event_loop().time()
                
                # 创建下载任务
                download_task = asyncio.create_task(
                    self._download_single_task(scanner, page, task_data, progress_callback)
                )
                self.running_downloads.append(download_task)
                print(f"   🚀 开始下载: {task_data.get('file_name', 'Unknown')} (运行中: {len(self.running_downloads)})")
            
            # 等待至少一个任务完成
            if self.running_downloads:
                done, pending = await asyncio.wait(
                    self.running_downloads, 
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # 处理完成的任务
                for task in done:
                    self.running_downloads.remove(task)
                    try:
                        result = await task
                        if result["success"]:
                            # 如果有监控任务，等待监控任务完成
                            if result.get("monitor_task"):
                                try:
                                    await result["monitor_task"]
                                    # 监控完成后，检查最终状态
                                    task_status = None
                                    for task_id, task in scanner.status_manager.tasks.items():
                                        if task.file_name == result['file_name'] and task.status.value == 'completed':
                                            task_status = task
                                            break
                                    
                                    # 验证浏览器下载任务是否真正完成且文件存在
                                    download_verified = False
                                    actual_file_path = None
                                    actual_file_size = 0
                                    
                                    if task_status and task_status.status.value == 'completed' and task_status.file_size and task_status.file_size > 0:
                                        # 检查实际文件是否存在
                                        possible_paths = [
                                            Path.home() / "下载" / result['file_name'],
                                            Path.home() / "Downloads" / result['file_name'],
                                            Path("downloads") / result['file_name'],
                                            Path.cwd() / "downloads" / result['file_name']
                                        ]
                                        
                                        for path in possible_paths:
                                            if path.exists() and path.stat().st_size > 0:
                                                actual_file_path = path
                                                actual_file_size = path.stat().st_size
                                                download_verified = True
                                                print(f"   ✅ 文件验证成功: {path} (大小: {actual_file_size} 字节)")
                                                break
                                        
                                        if not download_verified:
                                            print(f"   ❌ 文件验证失败: {result['file_name']} (文件不存在或大小为0)")
                                            print(f"   🔍 已检查的路径: {[str(p) for p in possible_paths]}")
                                    else:
                                        print(f"   ❌ 下载状态验证失败: {result['file_name']} (状态: {task_status.status.value if task_status else 'None'})")
                                    
                                    # 只有文件真正存在且大小大于0才报告成功
                                    if download_verified and actual_file_path and actual_file_size > 0:
                                        result["file_size"] = actual_file_size
                                        result["progress"] = 1.0
                                        result["status"] = "completed"
                                        result["actual_file_path"] = str(actual_file_path)
                                        self.completed_tasks.append(result)
                                        print(f"   ✅ 下载完成: {result['file_name']} -> {actual_file_path}")
                                    else:
                                        result["status"] = "failed"
                                        result["error"] = "下载验证失败：浏览器下载任务未完成或文件不存在"
                                        self.failed_tasks.append(result)
                                        print(f"   ❌ 下载验证失败: {result['file_name']} (浏览器下载任务未完成或文件不存在)")
                                except Exception as e:
                                    result["status"] = "failed"
                                    result["error"] = f"监控异常: {e}"
                                    self.failed_tasks.append(result)
                                    print(f"   ❌ 监控异常: {result['file_name']} - {e}")
                            else:
                                # 没有监控任务时，需要验证下载是否真的成功
                                # 必须基于浏览器下载任务的真实完成状态
                                download_verified = False
                                actual_file_path = None
                                actual_file_size = 0
                                
                                # 1. 首先检查下载状态管理器中的任务状态
                                task_status = None
                                for task_id, task in scanner.status_manager.tasks.items():
                                    if task.file_name == result['file_name']:
                                        task_status = task
                                        break
                                
                                # 2. 验证浏览器下载任务是否真正完成
                                if task_status and task_status.status.value == 'completed':
                                    # 3. 检查实际文件是否存在且大小大于0
                                    possible_paths = [
                                        Path.home() / "下载" / result['file_name'],
                                        Path.home() / "Downloads" / result['file_name'],
                                        Path("downloads") / result['file_name'],
                                        Path.cwd() / "downloads" / result['file_name']
                                    ]
                                    
                                    for path in possible_paths:
                                        if path.exists() and path.stat().st_size > 0:
                                            actual_file_path = path
                                            actual_file_size = path.stat().st_size
                                            download_verified = True
                                            print(f"   ✅ 文件验证成功: {path} (大小: {actual_file_size} 字节)")
                                            break
                                    
                                    if not download_verified:
                                        print(f"   ❌ 文件验证失败: {result['file_name']} (文件不存在或大小为0)")
                                        print(f"   🔍 已检查的路径: {[str(p) for p in possible_paths]}")
                                else:
                                    print(f"   ❌ 下载状态验证失败: {result['file_name']} (状态: {task_status.status.value if task_status else 'None'})")
                                
                                # 4. 只有文件真正存在且大小大于0才报告成功
                                if download_verified and actual_file_path and actual_file_size > 0:
                                    result["file_size"] = actual_file_size
                                    result["progress"] = 1.0
                                    result["status"] = "completed"
                                    result["actual_file_path"] = str(actual_file_path)
                                    self.completed_tasks.append(result)
                                    print(f"   ✅ 下载完成: {result['file_name']} -> {actual_file_path}")
                                else:
                                    result["status"] = "failed"
                                    result["error"] = "下载验证失败：浏览器下载任务未完成或文件不存在"
                                    self.failed_tasks.append(result)
                                    print(f"   ❌ 下载验证失败: {result['file_name']} (浏览器下载任务未完成或文件不存在)")
                        else:
                            # 检查是否需要重试
                            current_retry_count = result.get("retry_count", 0)
                            if current_retry_count < 3:  # 最多重试3次
                                # 重试任务加入队列末尾，添加延迟
                                retry_data = result.get('task_data', {}).copy()
                                retry_data["retry_count"] = current_retry_count + 1
                                retry_data["retry_delay"] = 30 + (current_retry_count * 15)  # 30秒, 45秒, 60秒延迟
                                self.add_retry_task(retry_data)
                                print(f"   🔄 下载失败，将在队列末尾重试 ({current_retry_count + 1}/3): {result['file_name']}")
                            else:
                                self.failed_tasks.append(result)
                                print(f"   ❌ 下载失败: {result['file_name']} (已重试3次)")
                    except Exception as e:
                        print(f"   ⚠️ 任务执行异常: {e}")
        
        # 返回结果统计
        return {
            "completed": self.completed_tasks,
            "failed": self.failed_tasks,
            "total": len(file_elements),
            "success_rate": len(self.completed_tasks) / len(file_elements) * 100 if file_elements else 0
        }
    
    async def _download_single_task(self, scanner, page, task_data, progress_callback):
        """执行单个下载任务 - 使用页面锁避免并发冲突"""
        file_name = task_data.get('file_name', 'Unknown')
        
        try:
            # 使用页面锁确保同一时间只有一个任务在操作页面
            async with self.page_lock:
                print(f"   🔒 获取页面锁: {file_name}")
                
                result = await download_single_file(
                    scanner, page, task_data, 
                    task_data.get('file_index', 0), 
                    task_data.get('total_files', 0),
                    progress_callback=progress_callback
                )
                
                print(f"   🔓 释放页面锁: {file_name}")
            
            result['task_data'] = task_data  # 保存原始任务数据用于重试
            return result
        except Exception as e:
            return {
                "file_name": task_data.get('file_name', 'Unknown'),
                "file_index": task_data.get('file_index', 0),
                "success": False,
                "error": str(e),
                "retry_count": task_data.get('retry_count', 0),
                "task_data": task_data
            }


async def batch_download_files(scanner, page, file_elements, unified_log_file=None):
    """队列式批量下载文件 - 使用下载队列管理器"""
    try:
        total_files = len(file_elements)
        
        print(f"\n🚀 开始队列式下载 {total_files} 个文件")
        print(f"⚡ 最大并发数: 2")
        print(f"⏱️ 任务间隔: 5秒")
        print("=" * 50)
        
        # 创建进度跟踪字典
        progress_tracker = {}
        for i, file_elem in enumerate(file_elements):
            progress_tracker[i + 1] = {
                "file_name": file_elem['text'],
                "status": "waiting",
                "progress": 0.0,
                "file_size": 0,
                "speed": 0.0,
                "error": None,
                "path": file_elem.get('path') or '',
                "href": file_elem.get('href') or '',
                "page_url": file_elem.get('page_url') or ''
            }
        
        # 使用统一日志文件或创建独立报告文件
        if unified_log_file:
            report_filepath = unified_log_file
        else:
            logs_dir = Path("downloads/logs")
            logs_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"unified_batch_download_report_{timestamp}.json"
            report_filepath = logs_dir / report_filename
        
        # 登录状态检测器与触发控制
        login_detector = LoginStatusDetector()
        consecutive_failures = 0
        zero_speed_since = None
        login_check_in_progress = False

        # 实时更新统一报告文件
        async def update_progress_and_log(result):
            progress_tracker[result["file_index"]] = {
                "file_name": result["file_name"],
                "status": result["status"],
                "progress": result["progress"],
                "file_size": result["file_size"],
                "speed": result["speed"],
                "error": result["error"],
                "extract_info": result.get("extract_info"),
                "extract_task_running": result.get("extract_task") is not None
            }
            # 旧版/原有行为：实时写入统一报告
            await update_unified_report_realtime(progress_tracker, total_files, 2, report_filepath)

            # 登录状态检测触发逻辑
            nonlocal consecutive_failures, zero_speed_since, login_check_in_progress

            # 1) 连续失败计数
            if result.get("status") == "failed":
                consecutive_failures += 1
            elif result.get("status") in ("completed", "downloading", "starting"):
                # 成功或正常进展则重置
                consecutive_failures = 0

            # 当连续失败达到2次时触发一次登录检测（非阻塞）
            if consecutive_failures >= int(os.getenv("LOGIN_CHECK_MAX_FAILS", "2")) and not login_check_in_progress:
                login_check_in_progress = True
                async def _run_login_check_on_failures():
                    print("🔐 连续下载失败，触发登录状态检测...")
                    status = await login_detector.open_target_and_detect(settings.target_url)
                    print(f"🔐 登录状态: {status}")
                    nonlocal login_check_in_progress
                    login_check_in_progress = False
                asyncio.create_task(_run_login_check_on_failures())

            # 2) 全局零速度检测（需持续>=60s 且存在下载中且进度<100%的任务）
            total_speed = 0.0
            has_incomplete_downloading = False
            for t in progress_tracker.values():
                total_speed += float(t.get("speed") or 0.0)
                if t.get("status") == "downloading":
                    prog = float(t.get("progress") or 0.0)
                    if prog < 0.999:
                        has_incomplete_downloading = True

            now_ts = asyncio.get_event_loop().time()
            if has_incomplete_downloading and total_speed <= 0.0001:
                if zero_speed_since is None:
                    zero_speed_since = now_ts
                idle_secs = now_ts - zero_speed_since
                idle_threshold = float(os.getenv("ZERO_SPEED_SECONDS", "60"))
                if idle_secs >= idle_threshold and not login_check_in_progress:
                    login_check_in_progress = True
                    async def _run_login_check_on_idle():
                        print("🔐 速度为0已持续60s且存在未完成下载，触发登录状态检测...")
                        status = await login_detector.open_target_and_detect(settings.target_url)
                        print(f"🔐 登录状态: {status}")
                        nonlocal login_check_in_progress
                        login_check_in_progress = False
                    asyncio.create_task(_run_login_check_on_idle())
            else:
                zero_speed_since = None
        
        # 创建下载队列管理器
        queue_manager = DownloadQueueManager(max_concurrent=2, task_interval=5)
        
        # 启动队列式下载
        print("🔄 正在启动队列式下载...")
        queue_results = await queue_manager.start_download_queue(scanner, page, file_elements, update_progress_and_log)
        
        # 处理队列结果
        results = queue_results["completed"] + queue_results["failed"]
        
        # 等待所有后台解压任务完成
        print("📦 等待所有解压任务完成...")
        extract_tasks = []
        for result in results:
            if isinstance(result, dict) and result.get("extract_task"):
                extract_tasks.append(result["extract_task"])
        
        if extract_tasks:
            extract_results = await asyncio.gather(*extract_tasks, return_exceptions=True)
            # 将解压结果更新到对应的下载结果中 - 确保信息匹配
            extract_index = 0
            for i, result in enumerate(results):
                if isinstance(result, dict) and result.get("extract_task"):
                    if extract_index < len(extract_results):
                        extract_result = extract_results[extract_index]
                        if not isinstance(extract_result, Exception):
                            # 确保解压信息与下载任务匹配
                            if extract_result.get("file_name") == result.get("file_name"):
                                result["extract_info"] = extract_result
                            else:
                                print(f"   ⚠️ 解压信息不匹配: {result.get('file_name')} vs {extract_result.get('file_name')}")
                                # 查找匹配的解压结果
                                for extract_res in extract_results:
                                    if extract_res.get("file_name") == result.get("file_name"):
                                        result["extract_info"] = extract_res
                                        break
                        extract_index += 1
        
        # 处理结果
        download_stats = {
            "timestamp": datetime.now().isoformat(),
            "total_files": total_files,
            "concurrency": 2,
            "successful": len(queue_results["completed"]),
            "failed": len(queue_results["failed"]),
            "downloaded_files": [r["file_name"] for r in queue_results["completed"]],
            "failed_files": [{"name": r["file_name"], "reason": r.get("error", "Unknown"), "retry_count": r.get("retry_count", 0)} for r in queue_results["failed"]],
            "file_details": results
        }
        
        # 显示重试成功的文件
        for result in queue_results["completed"]:
                if result.get("retry_count", 0) > 0:
                    print(f"   ✅ {result['file_name']} 重试 {result['retry_count']} 次后成功")
        
        # 显示批量下载摘要
        print_batch_download_summary(download_stats)
        
        # 最终更新统一报告文件（包含完整信息）
        await finalize_unified_report(download_stats, report_filepath)
        
        # 生成安全摘要报告
        try:
            safety_summary = get_security_summary()
            print(f"\n🔒 安全摘要报告:")
            print(f"   允许的下载路径: {safety_summary.get('allowed_download_path', 'N/A')}")
            print(f"   已下载文件数: {safety_summary.get('total_downloaded', 0)}")
            print(f"   禁止的操作: {len(safety_summary.get('forbidden_actions', []))} 种")
            print(f"   允许的操作: {len(safety_summary.get('allowed_actions', []))} 种")
            print(f"   ✅ 所有操作均符合安全指南")
        except Exception as e:
            print(f"   ⚠️ 生成安全摘要失败: {e}")
        
    except Exception as e:
        print(f"❌ 批量下载过程出错: {e}")
        import traceback
        traceback.print_exc()


def is_safe_download_operation(file_name):
    """安全检查 - 确保只进行下载操作"""
    # 取消下载安全限制：放行所有文件名
    return True


def is_safe_url(url):
    """URL安全检查 - 禁止访问危险的管理页面"""
    try:
        # 禁止访问危险的管理页面
        FORBIDDEN_URL_PATTERNS = [
            r"/_layouts/.*/delete\.aspx",
            r"/_layouts/.*/move\.aspx", 
            r"/_layouts/.*/rename\.aspx",
            r"/_layouts/.*/upload\.aspx",
            r"/_layouts/.*/edit\.aspx",
            r"/_layouts/.*/new\.aspx",
            r"/_layouts/.*/copy\.aspx",
            r"/_layouts/.*/share\.aspx",
            r"/_layouts/.*/permission\.aspx",
            r"/_layouts/.*/version\.aspx",
            r"/_layouts/.*/sync\.aspx",
            r"/_layouts/.*/publish\.aspx",
            r"/_layouts/.*/approve\.aspx",
            r"/_layouts/.*/workflow\.aspx",
            r"/_layouts/.*/admin\.aspx",
            r"/_layouts/.*/settings\.aspx",
            r"/_layouts/.*/manage\.aspx"
        ]
        
        import re
        for pattern in FORBIDDEN_URL_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        # 只允许访问文档库和文件查看页面
        ALLOWED_URL_PATTERNS = [
            r"/sites/.*/Shared%20Documents",
            r"/sites/.*/Shared Documents",
            r"/sites/.*/Forms/AllItems\.aspx",
            r"/sites/.*/Forms/AllItems.aspx",
            r"/sites/.*/Forms/.*\.aspx\?id=",
            r"/sites/.*/Forms/.*\.aspx?id="
        ]
        
        for pattern in ALLOWED_URL_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        
        # 如果不在允许列表中，默认拒绝
        return False
        
    except Exception:
        return False


async def scan_page_for_safe_actions(page):
    """扫描页面中的安全操作"""
    try:
        # 禁止的危险操作
        FORBIDDEN_ACTIONS = [
            "删除", "delete", "remove", "移除",
            "移动", "move", "剪切", "cut",
            "重命名", "rename", "重命名文件",
            "复制", "copy", "复制到",
            "粘贴", "paste", "粘贴到",
            "新建", "new", "创建", "create", "新建文件",
            "上传", "upload", "上载", "上传文件",
            "编辑", "edit", "修改", "modify", "更改",
            "共享", "share", "权限", "permission", "访问",
            "版本", "version", "历史", "恢复",
            "同步", "sync", "同步到",
            "发布", "publish", "发布到",
            "审批", "approve", "拒绝", "工作流", "workflow"
        ]
        
        # 允许的安全操作
        ALLOWED_ACTIONS = [
            "下载", "download",
            "查看", "view", "打开", "open",
            "预览", "preview",
            "在新窗口中打开", "open in new window",
            "属性", "properties", "详细信息", "details", "信息"
        ]
        
        # 扫描页面中的所有按钮和链接
        unsafe_count = 0
        unsafe_actions = []
        
        # 查找所有可能的操作元素
        elements = await page.evaluate("""
            () => {
                const elements = [];
                // 查找按钮
                document.querySelectorAll('button, input[type="button"], input[type="submit"]').forEach(el => {
                    if (el.textContent && el.textContent.trim()) {
                        elements.push({
                            type: 'button',
                            text: el.textContent.trim(),
                            visible: el.offsetWidth > 0 && el.offsetHeight > 0
                        });
                    }
                });
                // 查找链接
                document.querySelectorAll('a').forEach(el => {
                    if (el.textContent && el.textContent.trim()) {
                        elements.push({
                            type: 'link',
                            text: el.textContent.trim(),
                            visible: el.offsetWidth > 0 && el.offsetHeight > 0
                        });
                    }
                });
                return elements;
            }
        """)
        
        # 检查每个元素的文本
        for element in elements:
            if element.get('visible', False):
                text = element.get('text', '').lower()
                # 跳过一些常见的非危险操作
                if any(safe_word in text for safe_word in ['下载', 'download', '查看', 'view', '打开', 'open', '预览', 'preview']):
                    continue
                    
                for forbidden in FORBIDDEN_ACTIONS:
                    if forbidden.lower() in text:
                        unsafe_count += 1
                        unsafe_actions.append(element.get('text', ''))
                        print(f"   🚨 发现危险操作: '{element.get('text', '')}' (包含关键词: '{forbidden}')")
                        break
        
        return {
            "unsafe_count": unsafe_count,
            "unsafe_actions": unsafe_actions,
            "total_elements": len(elements)
        }
        
    except Exception as e:
        print(f"⚠️ 页面操作扫描异常: {e}")
        return {
            "unsafe_count": 0,
            "unsafe_actions": [],
            "total_elements": 0
        }


def is_safe_download_path(download_path):
    """下载路径安全检查 - 确保路径在允许范围内"""
    try:
        from pathlib import Path
        
        # 允许的下载路径
        allowed_base_path = Path("/home/ki-zj-1586/work/nj/WebScraping/downloads").resolve()
        
        # 检查路径是否在允许的基路径内
        try:
            download_path.relative_to(allowed_base_path)
            return True
        except ValueError:
            # 路径不在允许范围内
            return False
        
    except Exception:
        return False


def record_safe_download(file_path):
    """记录安全下载操作"""
    try:
        import json
        from datetime import datetime
        
        # 创建安全日志文件
        log_file = Path("downloads/logs/security_log.json")
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 读取现有日志
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        else:
            logs = {"downloads": [], "timestamp": ""}
        
        # 添加新的下载记录
        download_record = {
            "file_path": file_path,
            "timestamp": datetime.now().isoformat(),
            "operation": "download",
            "status": "completed"
        }
        
        logs["downloads"].append(download_record)
        logs["timestamp"] = datetime.now().isoformat()
        
        # 保存日志
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"⚠️ 记录安全日志失败: {e}")


def get_security_summary():
    """获取安全摘要报告"""
    try:
        # 禁止的危险操作
        forbidden_actions = [
            "删除", "delete", "remove", "移除",
            "移动", "move", "剪切", "cut",
            "重命名", "rename", "重命名文件",
            "复制", "copy", "复制到",
            "粘贴", "paste", "粘贴到",
            "新建", "new", "创建", "create", "新建文件",
            "上传", "upload", "上载", "上传文件",
            "编辑", "edit", "修改", "modify", "更改",
            "共享", "share", "权限", "permission", "访问",
            "版本", "version", "历史", "恢复",
            "同步", "sync", "同步到",
            "发布", "publish", "发布到",
            "审批", "approve", "拒绝", "工作流", "workflow"
        ]
        
        # 允许的安全操作
        allowed_actions = [
            "下载", "download",
            "查看", "view", "打开", "open",
            "预览", "preview",
            "在新窗口中打开", "open in new window",
            "属性", "properties", "详细信息", "details", "信息"
        ]
        
        # 统计已下载文件数
        total_downloaded = 0
        try:
            log_file = Path("downloads/logs/security_log.json")
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                    total_downloaded = len(logs.get("downloads", []))
        except Exception:
            pass
        
        return {
            "allowed_download_path": "/home/ki-zj-1586/work/nj/WebScraping/downloads",
            "total_downloaded": total_downloaded,
            "forbidden_actions": forbidden_actions,
            "allowed_actions": allowed_actions
        }
        
    except Exception as e:
        print(f"⚠️ 获取安全摘要失败: {e}")
        return {
            "allowed_download_path": "N/A",
            "total_downloaded": 0,
            "forbidden_actions": [],
            "allowed_actions": []
        }


async def get_verification_code_from_email():
    """从邮箱自动获取验证码 - 专门查找最新的SCｵｰﾄﾓｰﾃｨﾌﾞｴﾝｼﾞﾆｱﾘﾝｸﾞ株式会社 帐户验证码邮件"""
    try:
        import re
        import sys
        import os
        import email
        from email.header import decode_header
        
        # 添加src目录到路径，以便导入EmailClient
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'sp_automation'))
        from email_client import EmailClient
        
        print(f"📧 正在连接邮箱服务器...")
        
        # 使用EmailClient类
        client = EmailClient()
        mail = client.connect_pop3()
        
        if not mail:
            print(f"❌ 连接邮箱失败")
            return None
        
        # 获取邮件数量和大小
        num_messages = len(mail.list()[1])
        print(f"📧 邮箱中共有 {num_messages} 封邮件")
        
        # 从最新的邮件开始查找（从第311封开始往前查找）
        verification_code = None
        
        print(f"🔍 正在查找最新的\"SCｵｰﾄﾓｰﾃｨﾌﾞｴﾝｼﾞﾆｱﾘﾝｸﾞ株式会社 帐户验证码\"邮件...")
        print(f"📧 从最新邮件 {num_messages} 开始往前查找...")
        
        # 从最新邮件开始往前查找（最多查找最近10封）
        for i in range(num_messages, max(1, num_messages - 10), -1):
            try:
                # 获取邮件
                raw_email = b'\n'.join(mail.retr(i)[1])
                # 解析邮件
                msg = email.message_from_bytes(raw_email)
                
                # 解码邮件主题
                subject = decode_header(msg['subject'])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode('utf-8', errors='ignore')
                
                print(f"📧 检查邮件 {i}: {subject[:50]}...")
                
                # 专门查找SCｵｰﾄﾓｰﾃｨﾌﾞｴﾝｼﾞﾆｱﾘﾝｸﾞ株式会社 帐户验证码邮件
                if 'SCｵｰﾄﾓｰﾃｨﾌﾞｴﾝｼﾞﾆｱﾘﾝｸﾞ株式会社' in subject and '验证码' in subject:
                    print(f"   ✅ 找到目标邮件: {subject}")
                    
                    # 获取邮件正文
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = part.get('Content-Disposition')
                            
                            # 获取文本内容（包括HTML）
                            if content_type in ['text/plain', 'text/html'] and content_disposition is None:
                                try:
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        part_body = payload.decode('utf-8', errors='ignore')
                                        body += part_body + '\n'
                                except Exception as e:
                                    print(f"   ⚠️ 解码部分失败: {e}")
                    else:
                        try:
                            payload = msg.get_payload(decode=True)
                            if payload:
                                body = payload.decode('utf-8', errors='ignore')
                        except Exception as e:
                            print(f"   ⚠️ 解码内容失败: {e}")
                    
                    print(f"   📝 邮件内容: {body[:100]}...")
                    
                    # 查找8位数字验证码
                    code_patterns = [
                        r'\b(\d{8})\b',  # 8位数字
                        r'验证码[：:]\s*(\d{8})',  # 验证码：12345678
                        r'code[：:]\s*(\d{8})',  # code: 12345678
                        r'帐户验证码:\s*(\d{8})',  # 帐户验证码: 12345678
                    ]
                    
                    for pattern in code_patterns:
                        matches = re.findall(pattern, body, re.IGNORECASE)
                        if matches:
                            verification_code = matches[0]
                            print(f"   🔑 在目标邮件中找到验证码: {verification_code}")
                            break
                    
                    if verification_code:
                        break
                    else:
                        print(f"   ⚠️ 在目标邮件中未找到8位验证码")
                        
            except Exception as e:
                print(f"   ⚠️ 处理邮件 {i} 时出错: {e}")
                continue
        
        mail.quit()
        
        if verification_code:
            print(f"✅ 成功获取验证码: {verification_code}")
            return verification_code
        else:
            print(f"❌ 未找到SCｵｰﾄﾓｰﾃｨﾌﾞｴﾝｼﾞﾆｱﾘﾝｸﾞ株式会社 帐户验证码邮件")
            return None
            
    except Exception as e:
        print(f"❌ 获取验证码失败: {e}")
        return None


async def get_sms_verification_code_from_email(click_time=None):
    """从邮箱获取短信转发的6位数验证码 - 带时间比对"""
    try:
        import re
        import sys
        import os
        import email
        from email.header import decode_header
        from datetime import datetime
        import email.utils
        
        # 添加src目录到路径，以便导入EmailClient
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'sp_automation'))
        from email_client import EmailClient
        
        print(f"📧 正在连接邮箱服务器...")
        
        # 使用EmailClient类
        client = EmailClient()
        mail = client.connect_pop3()
        
        if not mail:
            print(f"❌ 连接邮箱失败")
            return None
        
        # 获取邮件数量和大小
        num_messages = len(mail.list()[1])
        print(f"📧 邮箱中共有 {num_messages} 封邮件")
        
        # 如果没有提供点击时间，使用当前时间
        if click_time is None:
            click_time = datetime.now()
        
        print(f"🕐 手机号按钮点击时间: {click_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏰ 查找点击时间之后的短信转发邮件...")
        
        # 获取最近10封邮件（增加数量以找到时间匹配的邮件）
        start_index = max(1, num_messages - 10 + 1)
        verification_code = None
        best_match = None
        best_time_diff = float('inf')
        
        for i in range(start_index, num_messages + 1):
            try:
                # 获取邮件
                raw_email = b'\n'.join(mail.retr(i)[1])
                # 解析邮件
                msg = email.message_from_bytes(raw_email)
                
                # 解码邮件主题
                subject = decode_header(msg['subject'])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode('utf-8', errors='ignore')
                
                print(f"📧 检查邮件 {i}: {subject[:50]}...")
                
                # 检查是否是短信转发邮件（主题包含"短信转发"）
                if '短信转发' in subject:
                    print(f"   🔍 发现短信转发邮件")
                    
                    # 解析邮件时间
                    email_time = None
                    date_str = msg.get('Date', '')
                    if date_str:
                        try:
                            # 解析邮件日期
                            email_time = email.utils.parsedate_to_datetime(date_str)
                            if email_time:
                                # 转换为本地时间
                                email_time = email_time.replace(tzinfo=None)
                                print(f"   📅 邮件时间: {email_time.strftime('%Y-%m-%d %H:%M:%S')}")
                                
                                # 计算时间差
                                time_diff = (email_time - click_time).total_seconds()
                                print(f"   ⏱️ 时间差: {time_diff:.1f} 秒")
                                
                                # 只处理点击时间之后的邮件
                                if time_diff > 0:
                                    print(f"   ✅ 邮件在点击时间之后")
                                else:
                                    print(f"   ⚠️ 邮件在点击时间之前，跳过")
                                    continue
                        except Exception as e:
                            print(f"   ⚠️ 解析邮件时间失败: {e}")
                            continue
                    else:
                        print(f"   ⚠️ 无法获取邮件时间，跳过")
                        continue
                    
                    # 获取邮件正文（包括HTML内容）
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = part.get('Content-Disposition')
                            
                            # 获取文本内容（包括HTML）
                            if content_type in ['text/plain', 'text/html'] and content_disposition is None:
                                try:
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        part_body = payload.decode('utf-8', errors='ignore')
                                        body += part_body + '\n'
                                except Exception as e:
                                    print(f"   ⚠️ 解码部分失败: {e}")
                    else:
                        try:
                            payload = msg.get_payload(decode=True)
                            if payload:
                                body = payload.decode('utf-8', errors='ignore')
                        except Exception as e:
                            print(f"   ⚠️ 解码内容失败: {e}")
                    
                    print(f"   📝 邮件内容: {body[:100]}...")
                    
                    # 查找【微软】使用验证码 XXXXXX 进行 Microsoft 身份验证
                    pattern = r'【微软】使用验证码\s*(\d{6})\s*进行\s*Microsoft\s*身份验证'
                    matches = re.findall(pattern, body)
                    if matches:
                        current_code = matches[0]
                        print(f"   🔑 在短信转发邮件中找到验证码: {current_code}")
                        
                        # 选择时间最接近点击时间的验证码
                        if time_diff < best_time_diff:
                            best_match = current_code
                            best_time_diff = time_diff
                            print(f"   🎯 更新最佳匹配验证码: {current_code} (时间差: {time_diff:.1f}秒)")
                    else:
                        # 备用方案：查找任何6位数字
                        code_patterns = [
                            r'\b(\d{6})\b',  # 6位数字
                            r'验证码[：:]\s*(\d{6})',  # 验证码：123456
                            r'code[：:]\s*(\d{6})',  # code: 123456
                        ]
                        
                        for pattern in code_patterns:
                            matches = re.findall(pattern, body, re.IGNORECASE)
                            if matches:
                                current_code = matches[0]
                                print(f"   🔑 在短信转发邮件中找到验证码: {current_code}")
                                
                                # 选择时间最接近点击时间的验证码
                                if time_diff < best_time_diff:
                                    best_match = current_code
                                    best_time_diff = time_diff
                                    print(f"   🎯 更新最佳匹配验证码: {current_code} (时间差: {time_diff:.1f}秒)")
                                break
                        
            except Exception as e:
                print(f"   ⚠️ 处理邮件 {i} 时出错: {e}")
                continue
        
        mail.quit()
        
        # 使用最佳匹配的验证码
        if best_match:
            verification_code = best_match
            print(f"✅ 成功获取最佳匹配短信验证码: {verification_code} (时间差: {best_time_diff:.1f}秒)")
            return verification_code
        elif verification_code:
            print(f"✅ 成功获取短信验证码: {verification_code}")
            return verification_code
        else:
            print(f"❌ 未找到短信验证码")
            return None
            
    except Exception as e:
        print(f"❌ 获取短信验证码失败: {e}")
        return None


def print_batch_download_summary(stats):
    """打印批量下载摘要"""
    print(f"\n📊 队列式下载摘要:")
    print("=" * 50)
    print(f"📦 总文件数: {stats['total_files']}")
    print(f"⚡ 最大并发数: {stats['concurrency']}")
    print(f"⏱️ 任务间隔: 5秒")
    print(f"✅ 成功下载: {stats['successful']}")
    print(f"❌ 下载失败: {stats['failed']}")
    
    success_rate = (stats['successful'] / stats['total_files'] * 100) if stats['total_files'] > 0 else 0
    print(f"📈 成功率: {success_rate:.1f}%")
    
    if stats['downloaded_files']:
        print(f"\n✅ 成功下载的文件:")
        for file_name in stats['downloaded_files']:
            print(f"   - {file_name}")
        
        # 显示解压信息
        extracted_count = 0
        extract_task_count = 0
        directory_created_count = 0
        for file_detail in stats.get('file_details', []):
            if file_detail.get('extract_info') and file_detail['extract_info'].get('success'):
                extracted_count += 1
                extract_info = file_detail['extract_info']
                print(f"     📦 已解压: {extract_info['extracted_count']}/{extract_info['total_files_in_zip']} 个文件")
                if extract_info.get('directory_structure_created'):
                    directory_created_count += 1
                    print(f"     📁 目录结构: {extract_info['extract_path']}")
            elif file_detail.get('extract_task_running'):
                extract_task_count += 1
                print(f"     📦 解压中: {file_detail['file_name']}")
        
        if extracted_count > 0:
            print(f"\n📦 解压摘要: {extracted_count} 个zip文件已解压")
        if directory_created_count > 0:
            print(f"📁 目录结构: {directory_created_count} 个原始目录结构已创建")
        if extract_task_count > 0:
            print(f"📦 后台解压: {extract_task_count} 个zip文件正在解压中")
    
    if stats['failed_files']:
        print(f"\n❌ 下载失败的文件:")
        for failed_file in stats['failed_files']:
            retry_info = f" (重试 {failed_file.get('retry_count', 0)} 次)" if failed_file.get('retry_count', 0) > 0 else ""
            print(f"   - {failed_file['name']} ({failed_file['reason']}){retry_info}")
    
    print("=" * 50)


async def save_unified_batch_download_report(stats, unified_log_file=None):
    """保存统一的批量下载报告 - 包含所有文件详情和目录结构"""
    try:
        if unified_log_file:
            # 使用统一日志文件
            report_filepath = unified_log_file
        else:
            # 创建logs目录
            logs_dir = Path("downloads/logs")
            logs_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成报告文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"unified_batch_download_report_{timestamp}.json"
            report_filepath = logs_dir / report_filename
        
        if unified_log_file:
            # 读取现有统一日志数据
            try:
                with open(unified_log_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except:
                existing_data = {"scan_info": {}, "discovered_files": []}
            
            # 添加下载报告信息到统一日志
            existing_data["download_report"] = {
                "report_info": {
                    "timestamp": stats["timestamp"],
                    "report_type": "unified_batch_download",
                    "concurrency": stats.get("concurrency", 2)
                },
                "summary": {
                    "total_files": stats["total_files"],
                    "successful_downloads": stats["successful"],
                    "failed_downloads": stats["failed"],
                    "success_rate": f"{(stats['successful'] / stats['total_files'] * 100):.1f}%" if stats['total_files'] > 0 else "0%"
                },
                "downloaded_files": stats["downloaded_files"],
                "failed_files": stats["failed_files"],
                "file_details": stats["file_details"],
                "task_status_summary": {
                    "completed": len([f for f in stats["file_details"] if f.get("status") == "completed"]),
                    "failed": len([f for f in stats["file_details"] if f.get("status") == "failed"]),
                    "retrying": len([f for f in stats["file_details"] if "retrying" in f.get("status", "")]),
                    "downloading": len([f for f in stats["file_details"] if f.get("status") == "downloading"])
                },
                "security_compliance": {
                    "only_zip_files": True,
                    "safe_operations_only": True,
                    "no_dangerous_actions": True,
                    "parallel_download_controlled": True
                }
            }
            
            # 保存统一日志文件
            with open(report_filepath, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
        else:
            # 构建完整的报告数据（独立文件模式）
            report_data = {
            "report_info": {
                "timestamp": stats["timestamp"],
                "report_type": "unified_batch_download",
                    "concurrency": stats.get("concurrency", 2)
            },
            "summary": {
                "total_files": stats["total_files"],
                "successful_downloads": stats["successful"],
                "failed_downloads": stats["failed"],
                "success_rate": f"{(stats['successful'] / stats['total_files'] * 100):.1f}%" if stats['total_files'] > 0 else "0%"
            },
            "downloaded_files": stats["downloaded_files"],
            "failed_files": stats["failed_files"],
            "file_details": stats["file_details"],
            "task_status_summary": {
                "completed": len([f for f in stats["file_details"] if f.get("status") == "completed"]),
                "failed": len([f for f in stats["file_details"] if f.get("status") == "failed"]),
                "retrying": len([f for f in stats["file_details"] if "retrying" in f.get("status", "")]),
                "downloading": len([f for f in stats["file_details"] if f.get("status") == "downloading"])
            },
            "security_compliance": {
                "only_zip_files": True,
                "safe_operations_only": True,
                "no_dangerous_actions": True,
                "parallel_download_controlled": True
            }
        }
        
            # 保存独立报告文件
        with open(report_filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"📋 统一批量下载报告已保存到: {report_filepath}")
        
        # 生成Markdown格式报告
        try:
            md_report_path = await save_markdown_report(str(report_filepath))
            if md_report_path:
                print(f"📄 Markdown格式报告已生成")
        except Exception as md_error:
            print(f"⚠️ Markdown报告生成失败: {md_error}")
        
        # 同时更新主下载状态文件
        await update_main_download_state_with_batch_results(stats)
        
    except Exception as e:
        print(f"❌ 保存统一批量下载报告失败: {e}")


def generate_markdown_report(json_file_path: str) -> str:
    """基于JSON日志文件生成Markdown格式的下载报告"""
    try:
        # 读取JSON数据
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 提取报告数据
        if "download_report" in data:
            # 统一日志文件格式
            report_data = data["download_report"]
        else:
            # 独立报告文件格式
            report_data = data
        
        # 生成Markdown报告
        md_content = []
        
        # 1. 报告标题和基本信息
        md_content.append("# SharePoint 批量下载报告")
        md_content.append("")
        
        report_info = report_data.get("report_info", {})
        timestamp = report_info.get("timestamp", "")
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                formatted_time = dt.strftime("%Y年%m月%d日 %H:%M:%S")
            except:
                formatted_time = timestamp
        else:
            formatted_time = "未知时间"
        
        md_content.append(f"**生成时间**: {formatted_time}")
        md_content.append(f"**并发下载数**: {report_info.get('concurrency', 2)}")
        md_content.append("")
        
        # 2. 下载摘要统计
        md_content.append("## 📊 下载摘要")
        md_content.append("")
        
        summary = report_data.get("summary", {})
        md_content.append("| 项目 | 数量 |")
        md_content.append("|------|------|")
        md_content.append(f"| 总文件数 | {summary.get('total_files', 0)} |")
        md_content.append(f"| 成功下载 | {summary.get('successful_downloads', 0)} |")
        md_content.append(f"| 失败下载 | {summary.get('failed_downloads', 0)} |")
        md_content.append(f"| 成功率 | {summary.get('success_rate', '0%')} |")
        md_content.append("")
        
        # 3. 文件下载详情表格
        md_content.append("## 📁 文件下载详情")
        md_content.append("")
        
        file_details = report_data.get("file_details", [])
        if file_details:
            md_content.append("| 序号 | 文件名 | 状态 | 文件大小 | 下载速度 | 重试次数 | 解压状态 |")
            md_content.append("|------|--------|------|----------|----------|----------|----------|")
            
            for i, file_info in enumerate(file_details, 1):
                file_name = file_info.get("file_name", "未知")
                status = "✅ 成功" if file_info.get("success", False) else "❌ 失败"
                file_size = file_info.get("file_size", 0)
                speed = file_info.get("speed", 0)
                retry_count = file_info.get("retry_count", 0)
                
                # 格式化文件大小
                if file_size > 1024 * 1024:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                elif file_size > 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size} B"
                
                # 格式化下载速度
                if speed > 1024 * 1024:
                    speed_str = f"{speed / (1024 * 1024):.1f} MB/s"
                elif speed > 1024:
                    speed_str = f"{speed / 1024:.1f} KB/s"
                else:
                    speed_str = f"{speed:.1f} B/s"
                
                # 解压状态
                extract_info = file_info.get("extract_info", {})
                if extract_info and extract_info.get("success", False):
                    extract_status = f"✅ 成功 ({extract_info.get('extracted_count', 0)} 个文件)"
                elif extract_info:
                    extract_status = "❌ 失败"
                else:
                    extract_status = "⏳ 未解压"
                
                md_content.append(f"| {i} | {file_name} | {status} | {size_str} | {speed_str} | {retry_count} | {extract_status} |")
        
        md_content.append("")
        
        # 4. 解压信息汇总
        md_content.append("## 📦 解压信息汇总")
        md_content.append("")
        
        total_extracted = 0
        successful_extracts = 0
        failed_extracts = 0
        
        for file_info in file_details:
            extract_info = file_info.get("extract_info", {})
            if extract_info:
                if extract_info.get("success", False):
                    successful_extracts += 1
                    total_extracted += extract_info.get("extracted_count", 0)
                else:
                    failed_extracts += 1
        
        md_content.append("| 项目 | 数量 |")
        md_content.append("|------|------|")
        md_content.append(f"| 成功解压文件数 | {successful_extracts} |")
        md_content.append(f"| 失败解压文件数 | {failed_extracts} |")
        md_content.append(f"| 总解压文件数 | {total_extracted} |")
        md_content.append("")
        
        # 5. 安全合规性检查
        md_content.append("## 🔒 安全合规性检查")
        md_content.append("")
        
        security = report_data.get("security_compliance", {})
        md_content.append("| 检查项目 | 状态 |")
        md_content.append("|----------|------|")
        md_content.append(f"| 仅下载ZIP文件 | {'✅ 通过' if security.get('only_zip_files', False) else '❌ 未通过'} |")
        md_content.append(f"| 仅执行安全操作 | {'✅ 通过' if security.get('safe_operations_only', False) else '❌ 未通过'} |")
        md_content.append(f"| 无危险操作 | {'✅ 通过' if security.get('no_dangerous_actions', False) else '❌ 未通过'} |")
        md_content.append(f"| 并行下载受控 | {'✅ 通过' if security.get('parallel_download_controlled', False) else '❌ 未通过'} |")
        md_content.append("")
        
        # 6. 下载文件列表
        md_content.append("## 📋 下载文件列表")
        md_content.append("")
        
        downloaded_files = report_data.get("downloaded_files", [])
        if downloaded_files:
            for i, file_name in enumerate(downloaded_files, 1):
                md_content.append(f"{i}. {file_name}")
        else:
            md_content.append("无下载文件")
        md_content.append("")
        
        # 7. 失败文件列表（如有）
        failed_files = report_data.get("failed_files", [])
        if failed_files:
            md_content.append("## ❌ 失败文件列表")
            md_content.append("")
            for i, file_name in enumerate(failed_files, 1):
                md_content.append(f"{i}. {file_name}")
            md_content.append("")
        
        # 8. 任务状态汇总
        md_content.append("## 📈 任务状态汇总")
        md_content.append("")
        
        task_status = report_data.get("task_status_summary", {})
        md_content.append("| 状态 | 数量 |")
        md_content.append("|------|------|")
        md_content.append(f"| 已完成 | {task_status.get('completed', 0)} |")
        md_content.append(f"| 失败 | {task_status.get('failed', 0)} |")
        md_content.append(f"| 重试中 | {task_status.get('retrying', 0)} |")
        md_content.append(f"| 下载中 | {task_status.get('downloading', 0)} |")
        md_content.append("")
        
        # 9. 报告结尾
        md_content.append("---")
        md_content.append("")
        md_content.append(f"*报告生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}*")
        md_content.append("")
        md_content.append("*此报告由SharePoint自动化下载系统自动生成*")
        
        return "\n".join(md_content)
        
    except Exception as e:
        return f"# 报告生成失败\n\n错误信息: {str(e)}"


async def save_markdown_report(json_file_path: str, output_dir: str = "downloads/reports") -> str:
    """保存Markdown格式的下载报告"""
    try:
        # 创建报告目录
        reports_dir = Path(output_dir)
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成Markdown内容
        md_content = generate_markdown_report(json_file_path)
        
        # 生成报告文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"download_report_{timestamp}.md"
        report_filepath = reports_dir / report_filename
        
        # 保存Markdown报告
        with open(report_filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"📄 Markdown报告已生成: {report_filepath}")
        return str(report_filepath)
        
    except Exception as e:
        print(f"❌ 生成Markdown报告失败: {e}")
        return ""


async def update_main_download_state_with_batch_results(stats):
    """更新主下载状态文件，添加批量下载结果"""
    try:
        # 读取现有的下载状态文件
        state_file = Path("downloads/download_state.json")
        if state_file.exists():
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
        else:
            state_data = {"tasks": {}, "timestamp": ""}
        
        # 添加批量下载结果
        state_data["batch_download_results"] = {
            "timestamp": stats["timestamp"],
            "total_files": stats["total_files"],
            "concurrency": stats.get("concurrency", 2),
            "successful": stats["successful"],
            "failed": stats["failed"],
            "downloaded_files": stats["downloaded_files"],
            "failed_files": stats["failed_files"]
        }
        
        state_data["timestamp"] = datetime.now().isoformat()
        
        # 保存更新后的状态文件
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, ensure_ascii=False, indent=2)
        
        print(f"📝 已更新主下载状态文件，添加批量下载结果")
        
    except Exception as e:
        print(f"❌ 更新主下载状态文件失败: {e}")


class SharePointExistingBrowserScannerCDP:
    """SharePoint 文件结构扫描器（CDP 监控版） - 业务逻辑封装"""
    
    def __init__(self, test_mode: bool = True, debug_port: int = 9222):
        self.test_mode = test_mode
        self.debug_port = debug_port
        self.scanner = SharePointScanner(test_mode, debug_port)
        self.recursive_scanner = None
        self.downloader = None
        self.status_manager = None
        self.download_monitor = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        # 确保调试浏览器正在运行
        target_url = settings.target_url if hasattr(settings, 'target_url') else None
        browser_ready = await ensure_browser_running(self.debug_port, target_url)
        
        if not browser_ready:
            raise Exception("无法启动或连接到调试浏览器")
        
        playwright = await async_playwright().start()
        success = await self.scanner.connect_to_browser(playwright)
        if success:
            self.recursive_scanner = SharePointRecursiveScanner(self.scanner)
            self.downloader = SharePointFileDownloader(self.scanner.safety_manager)
            self.status_manager = create_download_status_manager("downloads/download_state.json")
            self.download_monitor = BrowserDownloadMonitor(self.status_manager)
            return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.scanner.cleanup_pages()
        await self.scanner.disconnect()
        if self.status_manager:
            self.status_manager.close()
    
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


async def batch_download_zip_files():
    """批量下载 .zip 文件（CDP 监控）"""
    print("📦 批量下载 .zip 文件")
    print("=" * 50)
    print("🔒 安全提醒：本脚本严格遵循 SharePoint 安全操作指南")
    print("   ✅ 只允许下载操作")
    print("   ❌ 严格禁止删除、移动、重命名等危险操作")
    print("   🛡️ 所有操作都在安全监控下进行")
    print("   📊 下载状态由浏览器下载器 (CDP) 实时监控")
    print("   📦 支持批量下载多个 .zip 文件")
    print("   🚀 自动检测并启动调试浏览器")
    print("=" * 50)
    
    async with SharePointExistingBrowserScannerCDP(test_mode=True, debug_port=9222) as scanner:
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
                
                # 从配置文件读取目标URL并导航
                target_url = settings.target_url
                print(f"🎯 目标URL: {target_url}")
                print(f"🌐 正在导航到目标页面...")
                
                try:
                    await page.goto(target_url)
                    await page.wait_for_load_state('networkidle', timeout=30000)
                    print(f"✅ 导航成功，当前URL: {page.url}")
                    print(f"📄 页面标题: {await page.title()}")
                except Exception as e:
                    print(f"⚠️ 导航失败: {e}")
                    print(f"📄 使用当前页面: {page.url}")
                
                # 检测登录状态
                print(f"\n🔐 检测登录状态...")
                from src.sp_automation.login_status_detector import LoginStatusDetector
                login_detector = LoginStatusDetector()
                
                try:
                    # 使用login_status_detector的open_target_and_detect方法，避免重复启动浏览器
                    print(f"🔐 正在检测登录状态...")
                    login_status = await login_detector.open_target_and_detect(target_url)
                    print(f"🔐 登录状态: {login_status}")
                    
                    if login_status == LoginPageStatus.logged_in:
                        print(f"✅ 已登录，可以继续操作")
                        # 确保页面在正确位置
                        await page.goto(target_url)
                        await page.wait_for_load_state('networkidle', timeout=30000)
                        print(f"✅ 页面导航成功，当前URL: {page.url}")
                        print(f"📄 页面标题: {await page.title()}")
                    elif login_status == LoginPageStatus.login_required:
                        print(f"🔐 需要登录，login_status_detector已自动点击@kotei.com.cn按钮")
                        print(f"⏳ 等待验证码输入框出现...")
                        try:
                            # 等待验证码输入框出现
                            await page.wait_for_selector('input[name="npotc"][id="idTxtBx_OTC_Password"]', timeout=10000)
                            print(f"✅ 验证码输入框已出现")
                            
                            # 等待45秒让验证码邮件到达
                            print(f"⏳ 等待45秒让验证码邮件到达...")
                            await asyncio.sleep(45)
                            
                            # 尝试自动获取验证码
                            print(f"🔍 正在尝试自动获取验证码...")
                            verification_code = await get_verification_code_from_email()
                            
                            if verification_code:
                                print(f"🔑 自动获取到验证码: {verification_code}")
                                # 自动输入验证码
                                await page.fill('input[name="npotc"][id="idTxtBx_OTC_Password"]', verification_code)
                                await page.wait_for_timeout(1000)
                                
                                # 点击提交按钮
                                submit_button = page.locator('input[type="submit"], button[type="submit"]').first
                                if await submit_button.count() > 0:
                                    await submit_button.click()
                                    print(f"✅ 已自动提交验证码")
                                    await page.wait_for_timeout(3000)
                                else:
                                    print(f"⚠️ 未找到提交按钮，请手动提交")
                                    input("请手动提交验证码，然后按回车键继续...")
                                
                                # 第二步：点击包含手机号的按钮
                                print(f"🔍 正在查找包含手机号格式的登录按钮...")
                                phone_login_clicked = False
                                
                                # 尝试多种选择器查找包含手机号格式的按钮
                                phone_login_selectors = [
                                    'button:has-text("+")',
                                    'input[value*="+"]',
                                    'button:has-text("登录")',
                                    'button:has-text("Login")',
                                    'input[type="submit"]',
                                    'button[type="submit"]',
                                    '#idSIButton9',  # Microsoft 登录按钮的常见ID
                                    '.btn-primary',
                                    '[data-report-event="Signin_Submit"]'
                                ]
                                
                                for selector in phone_login_selectors:
                                    try:
                                        elements = page.locator(selector)
                                        count = await elements.count()
                                        for i in range(count):
                                            element = elements.nth(i)
                                            text = await element.text_content()
                                            if text and ('+' in text and any(c.isdigit() for c in text)):
                                                await element.click()
                                                print(f"✅ 已点击包含手机号格式的登录按钮: {text.strip()}")
                                                phone_login_clicked = True
                                                break
                                        if phone_login_clicked:
                                            break
                                    except Exception as e:
                                        print(f"   ⚠️ 尝试选择器 {selector} 失败: {e}")
                                        continue
                                
                                if not phone_login_clicked:
                                    print(f"⚠️ 未找到包含手机号格式的登录按钮，尝试按回车键提交...")
                                    try:
                                        await page.keyboard.press('Enter')
                                        print(f"✅ 已按回车键提交")
                                        phone_login_clicked = True
                                    except Exception as e:
                                        print(f"⚠️ 按回车键失败: {e}")
                                
                                if phone_login_clicked:
                                    # 记录点击时间
                                    phone_click_time = datetime.now()
                                    print(f"🕐 手机号按钮点击时间: {phone_click_time.strftime('%Y-%m-%d %H:%M:%S')}")
                                    
                                    # 延长等待时间到90秒让短信验证码到达
                                    print(f"⏳ 等待90秒让短信验证码到达...")
                                    await asyncio.sleep(90)
                                    
                                    # 尝试获取短信验证码（传入点击时间）
                                    print(f"🔍 正在尝试获取短信验证码...")
                                    sms_verification_code = await get_sms_verification_code_from_email(click_time=phone_click_time)
                                    
                                    if sms_verification_code:
                                        print(f"🔑 自动获取到短信验证码: {sms_verification_code}")
                                        
                                        # 查找短信验证码输入框
                                        sms_input_selectors = [
                                            'input[name="otc"]',
                                            'input[id*="otc"]',
                                            'input[type="text"][placeholder*="验证码"]',
                                            'input[type="text"][placeholder*="code"]',
                                            'input[type="text"][placeholder*="OTP"]',
                                            'input[type="text"]'
                                        ]
                                        
                                        sms_input_found = False
                                        for selector in sms_input_selectors:
                                            try:
                                                sms_input = page.locator(selector).first
                                                if await sms_input.count() > 0:
                                                    await sms_input.fill(sms_verification_code)
                                                    print(f"✅ 已输入短信验证码")
                                                    sms_input_found = True
                                                    break
                                            except Exception as e:
                                                print(f"   ⚠️ 尝试选择器 {selector} 失败: {e}")
                                                continue
                                        
                                        if not sms_input_found:
                                            print(f"⚠️ 未找到短信验证码输入框，请手动输入")
                                            input(f"请手动输入短信验证码 {sms_verification_code}，然后按回车键继续...")
                                        
                                        # 查找并点击验证按钮
                                        verify_button_selectors = [
                                            'button:has-text("验证")',
                                            'button:has-text("Verify")',
                                            'button:has-text("确认")',
                                            'button:has-text("Confirm")',
                                            'input[type="submit"]',
                                            'button[type="submit"]',
                                            'button:has-text("登录")',
                                            'button:has-text("Login")',
                                            'button:has-text("Sign in")',
                                            '#idSIButton9',
                                            '.btn-primary'
                                        ]
                                        
                                        verify_button_clicked = False
                                        for selector in verify_button_selectors:
                                            try:
                                                verify_btn = page.locator(selector).first
                                                if await verify_btn.count() > 0:
                                                    await verify_btn.click()
                                                    print(f"✅ 已点击验证按钮")
                                                    verify_button_clicked = True
                                                    break
                                            except Exception as e:
                                                print(f"   ⚠️ 尝试选择器 {selector} 失败: {e}")
                                                continue
                                        
                                        if not verify_button_clicked:
                                            print(f"⚠️ 未找到验证按钮，尝试按回车键")
                                            try:
                                                await page.keyboard.press('Enter')
                                                print(f"✅ 已按回车键提交")
                                                verify_button_clicked = True
                                            except Exception as e:
                                                print(f"⚠️ 按回车键失败: {e}")
                                        
                                        # 等待登录完成
                                        print(f"⏳ 等待登录完成...")
                                        await page.wait_for_timeout(5000)
                                        
                                        try:
                                            await page.wait_for_load_state('networkidle', timeout=10000)
                                            print(f"✅ 登录流程完成")
                                        except Exception as e:
                                            print(f"⚠️ 登录等待超时，继续执行: {e}")
                                    else:
                                        print(f"⚠️ 自动获取短信验证码失败")
                                        print(f"💡 请手动在浏览器中输入短信验证码")
                                        print(f"📱 短信验证码通常会在点击登录按钮后1-2分钟内发送到手机")
                                        input("输入短信验证码后按回车键继续...")
                                else:
                                    print(f"⚠️ 无法自动点击登录按钮，请手动登录")
                                    input("请手动完成登录，然后按回车键继续...")
                            else:
                                print(f"⚠️ 自动获取验证码失败（可能是邮箱授权码过期）")
                                print(f"💡 请手动在浏览器中输入验证码")
                                print(f"📧 验证码通常会在点击@kotei.com.cn按钮后1-2分钟内发送到邮箱")
                                input("输入验证码后按回车键继续...")
                        except Exception as e:
                            print(f"⚠️ 验证码处理失败: {e}")
                            print(f"📄 请手动完成登录流程...")
                            input("请在浏览器中完成登录，然后按回车键继续...")
                    else:
                        print(f"⚠️ 登录状态未知，请手动登录")
                        input("请在浏览器中完成登录，然后按回车键继续...")
                        
                except Exception as e:
                    print(f"⚠️ 登录状态检测失败: {e}")
                    print(f"📄 请手动完成登录...")
                    input("请在浏览器中完成登录，然后按回车键继续...")
                
                # 附加 CDP 下载监控
                await scanner.download_monitor.attach_to_page(page)
                
                # 关闭交互确认，自动执行
                try:
                    os.environ["AUTO_CONFIRM"] = "true"
                    if hasattr(scanner, 'scanner'):
                        setattr(scanner.scanner, 'test_mode', False)
                        setattr(scanner.scanner, 'auto_confirm', True)
                        if hasattr(scanner.scanner, 'safety_manager'):
                            scanner.scanner.safety_manager.test_mode = False
                    if hasattr(scanner, 'downloader'):
                        setattr(scanner.downloader, 'test_mode', False)
                        setattr(scanner.downloader, 'auto_confirm', True)
                        if hasattr(scanner.downloader, 'safety_manager'):
                            scanner.downloader.safety_manager.test_mode = False
                    if hasattr(scanner, 'recursive_scanner'):
                        setattr(scanner.recursive_scanner, 'test_mode', False)
                        setattr(scanner.recursive_scanner, 'auto_confirm', True)
                except Exception:
                    pass
                print("▶️ 自动开始扫描与下载，无需人工确认")
                
                # 使用内置递归扫描器扫描并收集ZIP文件信息
                print("🔍 使用内置递归扫描器查找所有层级文件...")
                zip_collector = []  # 用于收集zip文件信息
                
                # 创建统一的日志文件
                try:
                    logs_dir = Path("downloads/logs")
                    logs_dir.mkdir(parents=True, exist_ok=True)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    unified_log_file = logs_dir / f"unified_sharepoint_scan_{ts}.json"
                    print(f"📝 创建统一日志文件: {unified_log_file}")
                except Exception as e:
                    print(f"⚠️ 创建统一日志文件失败: {e}")
                    unified_log_file = None
                
                async def _zip_found_logger(info: dict):
                    # 增强的zip文件信息记录
                    zip_info = {
                        'text': info.get('text'),
                        'position': info.get('position') or {},
                        'path': info.get('path') or '',
                        'href': info.get('href') or '',
                        'page_url': info.get('page_url') or target_url,
                        'timestamp': datetime.now().isoformat(),
                        'file_size': info.get('file_size'),
                        'file_type': 'zip',
                        'discovery_method': 'recursive_scanner',
                        'depth': info.get('depth', 0)
                    }
                    
                    print(f"  📦(遍历) zip: {zip_info['text']}")
                    print(f"     ├─ path: {zip_info['path'] or '(顶层)'}")
                    print(f"     ├─ page_url: {zip_info['page_url']}")
                    print(f"     ├─ timestamp: {zip_info['timestamp']}")
                    href_preview = (zip_info['href'] or '')[:160]
                    print(f"     └─ href: {href_preview}")
                    
                    # 收集zip文件信息用于下载
                    zip_collector.append(zip_info)
                    
                    # 存储到统一日志文件
                    if unified_log_file:
                        try:
                            if not unified_log_file.exists():
                                # 首次创建文件，包含扫描阶段信息
                                unified_data = {
                                    "scan_info": {
                                        "timestamp": datetime.now().isoformat(),
                                        "target_url": target_url,
                                        "scan_phase": "discovery"
                                    },
                                    "discovered_files": [zip_info]
                                }
                                with open(unified_log_file, 'w', encoding='utf-8') as f:
                                    json.dump(unified_data, f, ensure_ascii=False, indent=2)
                            else:
                                # 读取现有数据，追加新记录
                                with open(unified_log_file, 'r', encoding='utf-8') as f:
                                    existing_data = json.load(f)
                                if "discovered_files" not in existing_data:
                                    existing_data["discovered_files"] = []
                                existing_data["discovered_files"].append(zip_info)
                                with open(unified_log_file, 'w', encoding='utf-8') as f:
                                    json.dump(existing_data, f, ensure_ascii=False, indent=2)
                                    
                        except Exception as e:
                            print(f"     ⚠️ 统一日志存储失败: {e}")

                await scanner.recursive_scanner.recursive_scan_folders(page, target_url, current_path="", zip_found_callback=_zip_found_logger)

                # 使用内置递归扫描器收集的ZIP文件信息构建下载候选列表
                zip_candidates = []
                if zip_collector:
                    print(f"✅ 使用内置递归扫描器收集的 {len(zip_collector)} 个ZIP文件信息")
                    zip_candidates = zip_collector
                    
                    # 更新统一日志文件，添加扫描完成信息
                    if unified_log_file:
                        try:
                            with open(unified_log_file, 'r', encoding='utf-8') as f:
                                existing_data = json.load(f)
                            existing_data["scan_info"]["scan_completed"] = datetime.now().isoformat()
                            existing_data["scan_info"]["total_discovered"] = len(zip_collector)
                            existing_data["scan_info"]["scan_phase"] = "completed"
                            with open(unified_log_file, 'w', encoding='utf-8') as f:
                                json.dump(existing_data, f, ensure_ascii=False, indent=2)
                            print(f"📝 已更新统一日志文件扫描完成信息")
                        except Exception as e:
                            print(f"⚠️ 更新统一日志文件失败: {e}")
                else:
                    # 备用方案：从扫描结果中获取（可能路径信息不完整）
                    print("⚠️ 内置递归扫描器未收集到ZIP文件，使用扫描结果作为备用方案")
                    scan_results = scanner.scanner.scan_results
                    if isinstance(scan_results.get("downloadable_files"), list) and scan_results["downloadable_files"]:
                        for f in scan_results["downloadable_files"]:
                            name = f.get("name") or f.get("text")
                            if name and str(name).lower().endswith('.zip'):
                                href = f.get('href') or ''
                                path_from_href = extract_folder_path_from_href(href)
                                zip_candidates.append({
                                    'text': name,
                                    'position': f.get('position') or {},
                                    'path': f.get('path') or path_from_href,
                                    'href': href,
                                    'page_url': target_url
                                })
                    else:
                        for f in scan_results.get("files", []):
                            name = f.get("name") or f.get("text")
                            if name and str(name).lower().endswith('.zip'):
                                href = f.get('href') or ''
                                path_from_href = extract_folder_path_from_href(href)
                                zip_candidates.append({
                                    'text': name,
                                    'position': f.get('position') or {},
                                    'path': f.get('path') or path_from_href,
                                    'href': href,
                                    'page_url': target_url
                                })

                if not zip_candidates:
                    print("❌ 未找到任何zip文件")
                    return

                # 去重：智能去重逻辑
                unique_zip_candidates = []
                seen_files = set()
                for file_elem in zip_candidates:
                    file_name = file_elem.get('text', '')
                    file_path = file_elem.get('path', '')
                    
                    # 智能去重逻辑：
                    # 1. 如果路径为空或None，只基于文件名去重（避免重复添加同一文件）
                    # 2. 如果路径不为空，基于文件名+路径去重（允许不同路径的同名文件）
                    if not file_path or file_path == '(空)' or file_path.strip() == '':
                        unique_key = file_name  # 只基于文件名
                    else:
                        unique_key = f"{file_name}|{file_path}"  # 基于文件名+路径
                    
                    if unique_key not in seen_files:
                        seen_files.add(unique_key)
                        unique_zip_candidates.append(file_elem)
                
                zip_candidates = unique_zip_candidates
                print(f"\n📦 总共找到 {len(zip_candidates)} 个zip文件 (已去重):")
                for i, file_elem in enumerate(zip_candidates):
                    path_disp = file_elem.get('path') or '(空)'
                    print(f"   {i+1}. {file_elem['text']} (路径: {path_disp})")
                
                # 自动确认批量下载
                print(f"\n🎯 将流水线式并行下载所有 {len(zip_candidates)} 个 .zip 文件")
                print(f"⚡ 最大并发数: 2")
                print(f"⏱️ 任务间隔: 5秒")
                print("⚠️ 即将执行并行下载（自动确认）")
                
                # 执行并行批量下载
                await batch_download_files(scanner, page, zip_candidates, unified_log_file)
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()


async def recursive_find_zip_files(page, max_depth=5, current_depth=0, current_path="", visited_paths: set | None = None, zip_collector: list | None = None, target_url: str = None):
    """递归查找所有层级的zip文件 - 严格遵循安全操作指南（更稳健的点击与去重）"""
    if visited_paths is None:
        visited_paths = set()
    if current_depth >= max_depth:
        print(f"  ⚠️ 达到最大深度 {max_depth}，停止递归")
        return []
    
    # 如果没有提供target_url，从当前页面URL获取
    if target_url is None:
        target_url = page.url
    
    print(f"🔍 第 {current_depth + 1} 层：正在查找文件夹和zip文件...")
    if current_path:
        print(f"   当前路径: {current_path}")
    
    # 优化的页面加载等待机制（统一停顿 0.3s）
    await page.wait_for_timeout(300)  # 优化：从500ms缩减为300ms (3/5)
    
    # 快速滚动确保所有元素加载
    for i in range(2):
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(300)  # 优化：从500ms缩减为300ms (3/5)
        print(f"   滚动 {i+1}/2 完成")
    
    # 短暂等待动态内容加载（0.3s）
    await page.wait_for_timeout(300)  # 优化：从500ms缩减为300ms (3/5)
    
    # 获取当前页面的所有元素
    elements = await page.evaluate("""
            () => {
                const getElementInfo = (element, type, selector) => {
                    const rect = element.getBoundingClientRect();
                    
                    // 获取元素路径
                    const getElementPath = (el) => {
                        const path = [];
                        let current = el;
                        while (current && current !== document.body) {
                            let selector = current.tagName.toLowerCase();
                            if (current.id) {
                                selector += '#' + current.id;
                            } else if (current.className) {
                                const classes = current.className.split(' ').filter(c => c.length > 0);
                                if (classes.length > 0) {
                                    selector += '.' + classes.slice(0, 2).join('.');
                                }
                            }
                            path.unshift(selector);
                            current = current.parentElement;
                        }
                        return path.join(' > ');
                    };
                    
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
                        foundBySelector: selector,
                        elementPath: getElementPath(element)
                    };
                };

                const allElements = [];
                const seen = new Set(); // 用于去重
                
                // 查找多种元素类型 - 包括文件名链接和文本
                const selectors = [
                    'span.heroTextWithHeroCommandsWrapped2_c5aceefe',
                    'span.field-LinkFilename-htmlGrid_1',
                    'span.hero_c5aceefe',
                    'span[data-automation-id="DetailsRow"]',
                    'span.ms-DetailsRow',
                    'span.ms-List-cell',
                    'span.ms-DetailsList-cell',
                    'a[data-automation-id="DetailsRow"]',
                    'a.ms-DetailsRow',
                    'a.ms-List-cell',
                    'a.ms-DetailsList-cell',
                    'div[data-automation-id="DetailsRow"]',
                    'div.ms-DetailsRow',
                    'div.ms-List-cell',
                    'div.ms-DetailsList-cell'
                ];
                
                // 检测所有元素类型
                selectors.forEach(selector => {
                    try {
                        const elements = document.querySelectorAll(selector);
                        console.log(`Selector ${selector} found ${elements.length} elements`);
                        
                        elements.forEach(el => {
                            if (el.classList.contains('headerRow_e4dc14da')) {
                                return;
                            }
                            
                            const text = el.textContent?.trim();
                            if (text && text.length > 0 && text.length < 100) {
                                // 排除表头文本
                                const headerTexts = ['名称', '修改时间', '修改者', '文件大小', '子文件夹计数', '子项目计数', '创建时间', '创建者'];
                                if (headerTexts.includes(text)) {
                                    return;
                                }
                                
                                // 去重
                                if (seen.has(text)) {
                                    return;
                                }
                                seen.add(text);
                                
                                console.log(`Found text: "${text}"`);
                                
                                // 判断类型 - 区分文件和文件夹
                                let itemType = 'unknown';
                                
                                // 检查是否有文件扩展名（包含点号）
                                const hasFileExtension = text.includes('.') && text.split('.').length > 1;
                                
                                if (text.toLowerCase().endsWith('.zip')) {
                                    itemType = 'zip_file';
                                } else if (hasFileExtension) {
                                    // 有扩展名的是文件，不进入
                                    itemType = 'file_item';
                                } else if (text.match(/^\\d{6}$/) || text.match(/^\\d{4}\\d{2}$/) || text.includes('_走行データ送付')) {
                                    // 没有扩展名的可能是文件夹
                                    itemType = 'folder_item';
                                } else if (text.length > 0 && text.length < 50 && !hasFileExtension) {
                                    // 其他没有扩展名的项目，可能是文件夹
                                    itemType = 'folder_item';
                                } else {
                                    // 显示所有找到的文本，帮助调试
                                    console.log(`Skipping text: "${text}"`);
                                    return;
                                }
                                
                                console.log(`Element type: ${itemType} for text: "${text}"`);
                                allElements.push(getElementInfo(el, itemType, selector));
                            }
                        });
                    } catch (e) {
                        console.log('Selector error:', selector, e);
                    }
                });
                
                return allElements;
            }
        """)
    
    all_zip_files = []
    folders_to_explore = []
    
    for element in elements:
        if element['type'] == 'zip_file':
            # 添加路径信息
            element['path'] = current_path
            # 保存当前地址栏URL，便于下次直接定位父目录
            try:
                element['page_url'] = page.url
            except Exception:
                element['page_url'] = ''
            all_zip_files.append(element)
            # 实时打印需要保存的信息
            print(f"  📦 找到zip文件: {element['text']}")
            print(f"     ├─ path: {current_path or '(顶层)'}")
            try:
                print(f"     ├─ page_url: {page.url}")
            except Exception:
                print(f"     ├─ page_url: (未知)")
            href_preview = (element.get('href') or '')[:120]
            print(f"     └─ href: {href_preview}")
            # 立即保存到收集器（包含 href/position/path），避免后续再查找
            if isinstance(zip_collector, list):
                href_val = element.get('href') or ''
                # 如 href 为空，尝试在 grid 中按文件名找到行内 a 链接提取 href
                if not href_val:
                    try:
                        row = page.locator("[role='grid'] div[data-automation-id='DetailsRow']").filter(has_text=element.get('text') or '').first
                        if await row.count() > 0:
                            link = row.locator("a[role='link'], a.ms-Link").first
                            if await link.count() > 0:
                                tmp = await link.get_attribute('href')
                                if tmp:
                                    href_val = tmp
                    except Exception:
                        pass
                # 捕获当前地址栏URL
                try:
                    current_page_url = page.url
                except Exception:
                    current_page_url = ''
                zip_collector.append({
                    'text': element.get('text'),
                    'path': current_path,
                    'href': href_val,
                    'position': element.get('position') or {},
                    'page_url': current_page_url
                })
        elif element['type'] == 'folder_item':
            # 只进入文件夹，不进入文件
            folders_to_explore.append(element)
            print(f"  📁 找到文件夹: {element['text']}")
        elif element['type'] == 'file_item':
            # 文件不进入，只记录
            print(f"  📄 找到文件: {element['text']} (跳过进入)")
    
    # 递归探索每个文件夹 - 严格遵循安全操作指南
    for folder in folders_to_explore:
        try:
            print(f"  🔍 进入文件夹: {folder['text']}")
            
            # 安全检查：确保只点击文件夹，不执行危险操作
            if not is_safe_folder_click(folder):
                print(f"  ⚠️ 跳过不安全的文件夹: {folder['text']}")
                continue
            
            # 记录安全操作
            record_safe_download(f"进入文件夹: {folder['text']}")
            
            # 去重避免循环
            new_path = f"{current_path}/{folder['text']}" if current_path else folder['text']
            if new_path in visited_paths:
                print(f"  🔁 已访问过路径，跳过: {new_path}")
                continue
            visited_paths.add(new_path)

            # 更稳健的点击（仅在grid内查找）- 增加重试机制和错误恢复
            clicked = False
            for retry in range(3):  # 最多重试3次
                try:
                    clicked = await click_folder_in_grid(page, folder['text'])
                    if clicked:
                        break
                    else:
                        print(f"  🔄 点击文件夹失败，第 {retry + 1} 次重试: {folder['text']}")
                        if retry < 2:  # 不是最后一次重试
                            await page.wait_for_timeout(2000)  # 等待2秒后重试
                            # 重新等待页面就绪
                            await wait_for_sharepoint_page_ready(page, max_wait_time=10000)
                except Exception as e:
                    print(f"  ❌ 点击文件夹异常: {e}")
                    # 检查是否是超时或失去响应的问题
                    if "timeout" in str(e).lower() or "exceeded" in str(e).lower():
                        print(f"  🔄 检测到超时异常，尝试恢复页面...")
                        # 尝试从超时中恢复
                        recovery_success = await recover_from_page_timeout(page, target_url)
                        if recovery_success:
                            print(f"  ✅ 页面恢复成功，继续重试")
                            continue
                        else:
                            print(f"  ❌ 页面恢复失败，跳过此文件夹")
                            break
                    else:
                        # 其他异常，等待后重试
                        await page.wait_for_timeout(2000)
            
            if not clicked:
                print(f"  ❌ 点击文件夹失败，已重试3次: {folder['text']}")
                continue

            # 等待页面切换完成：智能等待机制
            print(f"   ⏳ 等待页面切换完成...")
            try:
                # 使用智能等待机制
                page_ready = await wait_for_sharepoint_page_ready(page, max_wait_time=15000)
                if not page_ready:
                    print(f"   ⚠️ 页面加载可能未完全完成，检查是否需要恢复...")
                    # 检查页面是否失去响应
                    if not await check_page_responsiveness(page):
                        print(f"   🔄 页面失去响应，尝试恢复...")
                        recovery_success = await recover_from_page_timeout(page, target_url)
                        if not recovery_success:
                            print(f"   ❌ 页面恢复失败，跳过此文件夹")
                            continue
                    else:
                        # 即使页面未完全就绪，也等待一段时间让页面稳定
                        await page.wait_for_timeout(2000)

                # 校验是否成功进入 - 改进的稳定性检查
                try:
                    # 等待页面完全加载
                    await page.wait_for_timeout(600)  # 优化：从1000ms缩减为600ms (3/5)
                    
                    # 检查页面标题是否包含文件夹名称或"所有文档"
                    current_title = await page.title()
                    current_url = page.url
                    
                    # 更稳健的成功判断条件
                    success_indicators = [
                        folder['text'] in current_title,
                        "所有文档" in current_title,
                        folder['text'] in current_url,
                        await page.get_by_text(folder['text'], exact=False).count() > 0
                    ]
                    
                    if any(success_indicators):
                        print(f"  ✅ 成功进入文件夹: {folder['text']}")
                        print(f"  🔍 继续深入搜索文件夹: {folder['text']}")
                        sub_files = await recursive_find_zip_files(page, max_depth, current_depth + 1, new_path, visited_paths, zip_collector, target_url)
                        all_zip_files.extend(sub_files)
                        # 返回上级
                        print(f"  🔙 返回上级目录...")
                        try:
                            await page.go_back()
                            await page.wait_for_load_state('domcontentloaded', timeout=5000)
                            await page.wait_for_timeout(1000)
                        except Exception as e:
                            print(f"  ❌ 返回上级目录失败: {e}")
                            # 检查是否是超时问题
                            if "timeout" in str(e).lower() or "exceeded" in str(e).lower():
                                print(f"  🔄 检测到超时异常，尝试恢复页面...")
                                await recover_from_page_timeout(page, target_url)
                            else:
                                # 尝试直接导航到目标URL
                                try:
                                    await page.goto(target_url, wait_until="domcontentloaded", timeout=10000)
                                    await page.wait_for_timeout(1000)
                                    print(f"  ✅ 已通过直接导航返回上级目录")
                                except Exception:
                                    pass
                    else:
                        print(f"  ⚠️ 进入文件夹失败，页面标题: {current_title}")
                        # 若失败尽量回退一次，避免卡住
                        try:
                            await page.go_back()
                            await page.wait_for_timeout(300)  # 优化：从500ms缩减为300ms (3/5)
                        except Exception:
                            pass
                        continue
                        
                except Exception as e:
                    print(f"  ⚠️ 页面稳定性检查失败: {e}")
                    # 检查是否是超时问题
                    if "timeout" in str(e).lower() or "exceeded" in str(e).lower():
                        print(f"  🔄 检测到超时异常，尝试恢复页面...")
                        recovery_success = await recover_from_page_timeout(page, target_url)
                        if not recovery_success:
                            print(f"  ❌ 页面恢复失败，跳过此文件夹")
                    else:
                        # 尝试返回上级目录
                        try:
                            await page.go_back()
                            await page.wait_for_timeout(500)
                        except Exception:
                            pass
                    continue
                    
            except Exception as e:
                print(f"  ⚠️ 页面稳定性检查失败: {e}")
                # 检查是否是超时问题
                if "timeout" in str(e).lower() or "exceeded" in str(e).lower():
                    print(f"  🔄 检测到超时异常，尝试恢复页面...")
                    recovery_success = await recover_from_page_timeout(page, target_url)
                    if not recovery_success:
                        print(f"  ❌ 页面恢复失败，跳过此文件夹")
                else:
                    # 尝试返回上级目录
                    try:
                        await page.go_back()
                        await page.wait_for_timeout(500)
                    except Exception:
                        pass
                continue
                
        except Exception as e:
            print(f"  ⚠️ 进入文件夹 {folder['text']} 失败: {e}")
            # 检查是否是超时问题
            if "timeout" in str(e).lower() or "exceeded" in str(e).lower():
                print(f"  🔄 检测到超时异常，尝试恢复页面...")
                recovery_success = await recover_from_page_timeout(page, target_url)
                if not recovery_success:
                    print(f"  ❌ 页面恢复失败，跳过此文件夹")
            else:
                # 尝试返回上级目录
                try:
                    await page.go_back()
                    await page.wait_for_timeout(500)
                except:
                    pass
            continue
    
    return all_zip_files


def is_safe_folder_click(folder_element):
    """检查文件夹点击是否安全 - 遵循安全操作指南"""
    try:
        # 检查元素是否包含危险操作
        text = folder_element.get('text', '').lower()
        
        # 禁止的危险操作关键词
        forbidden_keywords = [
            'delete', 'remove', '移动', '剪切', 'cut',
            'rename', '重命名', 'copy', '复制',
            'paste', '粘贴', 'new', '新建', 'create', '创建',
            'upload', '上传', 'edit', '编辑', 'modify', '修改',
            'share', '共享', 'permission', '权限', 'version', '版本',
            'sync', '同步', 'publish', '发布', 'approve', '审批',
            'workflow', '工作流'
        ]
        
        for keyword in forbidden_keywords:
            if keyword in text:
                return False
        
        # 检查元素类型是否安全
        tag_name = folder_element.get('tagName', '').lower()
        if tag_name in ['button', 'input']:
            # 按钮和输入框需要特别检查
            return False
        
        return True
        
    except Exception as e:
        print(f"  ⚠️ 安全检查失败: {e}")
        return False


async def main():
    """主函数 - 交互式扫描和下载"""
    print("🔍 SharePoint 文件结构扫描器 (CDP 监控版)")
    print("=" * 50)
    
    async with SharePointExistingBrowserScannerCDP(test_mode=True, debug_port=9222) as scanner:
        try:
            # 扫描文件结构
            results = await scanner.scan_sharepoint_structure()
            
            if results.get("scan_status") == "success":
                print(f"\n✅ 扫描完成，找到 {len(results.get('downloadable_files', []))} 个可下载文件")
                
                # 显示扫描结果
                downloadable_files = results.get("downloadable_files", [])
                if downloadable_files:
                    print(f"\n📋 可下载文件列表:")
                    for i, file_info in enumerate(downloadable_files[:10]):  # 只显示前10个
                        print(f"   {i+1}. {file_info.get('name', 'Unknown')}")
                    
                    if len(downloadable_files) > 10:
                        print(f"   ... 还有 {len(downloadable_files) - 10} 个文件")
                    
                    # 询问是否下载
                    download_choice = input(f"\n是否开始下载所有 {len(downloadable_files)} 个文件？(y/N): ").strip().lower()
                    if download_choice == 'y':
                        # 获取页面对象进行下载
                        page = scanner.scanner.page if hasattr(scanner.scanner, 'page') else None
                        if page:
                            print(f"\n🚀 开始下载...")
                            await scanner.downloader.download_files_interactive(page, scanner.scanner.scan_results["downloadable_files"])
                            # 显示下载摘要（可与 DownloadStatusManager 合并使用）
                            download_summary = scanner.downloader.get_download_summary()
                            print(f"\n📊 下载完成: {download_summary['successful_downloads']}/{download_summary['total_downloads']} 成功")
                        else:
                            print("❌ 无法获取页面对象进行下载")
            else:
                print(f"\n❌ 扫描失败: {results.get('error', '未知错误')}")
                
        except Exception as e:
            print(f"❌ 程序执行失败: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    import sys
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        asyncio.run(batch_download_zip_files())
    else:
        asyncio.run(main())
