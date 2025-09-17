"""
SharePoint 安全操作模块
严格限制只能进行安全的只读操作，禁止任何可能影响文件状态的操作
"""

import os
import re
import urllib.parse
from pathlib import Path
from typing import List, Optional, Dict, Any, Set, Tuple
from playwright.async_api import Page
from .page_operations import navigate_to_url, find_element_by_text


class SharePointSafetyManager:
    """SharePoint 安全操作管理器"""
    
    # 严格禁止的操作按钮文本
    FORBIDDEN_ACTIONS = {
        "删除", "delete", "remove", "移除",
        "移动", "move", "剪切", "cut",
        "重命名", "rename", "重命名文件", "rename file",
        "复制", "copy", "复制到", "copy to",
        "粘贴", "paste", "粘贴到", "paste to",
        "新建", "new", "创建", "create", "新建文件", "new file",
        "上传", "upload", "上载", "上传文件", "upload file",
        "编辑", "edit", "修改", "modify", "更改", "change",
        "共享", "share", "权限", "permission", "访问", "access",
        "版本", "version", "历史", "history", "恢复", "restore",
        "同步", "sync", "同步到", "sync to",
        "发布", "publish", "发布到", "publish to",
        "审批", "approve", "拒绝", "reject", "工作流", "workflow"
    }
    
    # 允许的安全操作
    ALLOWED_ACTIONS = {
        "下载", "download", "查看", "view", "预览", "preview",
        "打开", "open", "在新窗口中打开", "open in new window",
        "属性", "properties", "详细信息", "details", "信息", "info"
    }
    
    # 禁止的 URL 模式
    FORBIDDEN_URL_PATTERNS = [
        r"/_layouts/.*/delete\.aspx",
        r"/_layouts/.*/move\.aspx", 
        r"/_layouts/.*/rename\.aspx",
        r"/_layouts/.*/copy\.aspx",
        r"/_layouts/.*/upload\.aspx",
        r"/_layouts/.*/new\.aspx",
        r"/_layouts/.*/edit\.aspx",
        r"/_layouts/.*/share\.aspx",
        r"/_layouts/.*/permissions\.aspx",
        r"/_layouts/.*/version\.aspx",
        r"/_layouts/.*/workflow\.aspx"
    ]
    
    def __init__(self, allowed_download_path: str = "downloads", allowed_sharepoint_path: str = None, test_mode: bool = False):
        """
        初始化安全管理器
        
        Args:
            allowed_download_path: 允许的下载路径，必须是相对路径
            allowed_sharepoint_path: 允许的 SharePoint 路径（如 "Test"），限制只能在此路径下操作
            test_mode: 测试模式，在测试模式下所有操作需要用户确认
        """
        self.allowed_download_path = Path(allowed_download_path).resolve()
        self.current_working_directory = Path.cwd()
        
        # 确保下载路径在项目目录内
        if not self.allowed_download_path.is_relative_to(self.current_working_directory):
            raise ValueError(f"下载路径必须在项目目录内: {self.current_working_directory}")
        
        # 创建下载目录
        self.allowed_download_path.mkdir(parents=True, exist_ok=True)
        
        # 记录已下载的文件
        self.downloaded_files: Set[str] = set()
        
        # SharePoint 路径限制
        self.allowed_sharepoint_path = allowed_sharepoint_path
        self.current_sharepoint_path = None
        
        # 测试模式
        self.test_mode = test_mode
        if test_mode:
            print("🧪 测试模式已启用 - 所有操作需要用户确认")
    
    async def request_user_confirmation_with_hover(
        self, 
        page, 
        action_description: str, 
        element_info: Dict[str, Any] = None,
        element_selector: str = None
    ) -> bool:
        """
        请求用户确认操作（测试模式）- 带鼠标悬停
        
        Args:
            page: 页面对象
            action_description: 操作描述
            element_info: 元素信息
            element_selector: 元素选择器（用于悬停）
            
        Returns:
            bool: 用户是否确认
        """
        if not self.test_mode:
            return True
        
        # 如果有元素选择器，先悬停到元素上
        if element_selector:
            try:
                element = await page.wait_for_selector(element_selector, timeout=5000)
                if element:
                    # 滚动到元素可见
                    await element.scroll_into_view_if_needed()
                    await page.wait_for_timeout(500)
                    
                    # 悬停到元素上
                    await element.hover()
                    await page.wait_for_timeout(1000)
                    
                    print(f"🖱️ 鼠标已悬停到目标元素上")
            except Exception as e:
                print(f"⚠️ 悬停失败: {e}")
        
        print(f"\n🧪 测试模式 - 需要用户确认操作:")
        print(f"   操作: {action_description}")
        
        if element_info:
            print(f"   元素文本: {element_info.get('text', 'N/A')}")
            print(f"   元素类型: {element_info.get('tagName', 'N/A')}")
            if element_info.get('position'):
                pos = element_info['position']
                print(f"   元素位置: ({pos.get('x', 0)}, {pos.get('y', 0)})")
        
        while True:
            try:
                response = input("   是否继续执行此操作? (y/n/s=跳过所有确认): ").strip().lower()
                if response in ['y', 'yes', '是']:
                    return True
                elif response in ['n', 'no', '否']:
                    print("   ❌ 用户取消操作")
                    return False
                elif response in ['s', 'skip', '跳过']:
                    print("   ⏭️ 跳过所有后续确认")
                    self.test_mode = False
                    return True
                else:
                    print("   请输入 y(是)/n(否)/s(跳过所有确认)")
            except KeyboardInterrupt:
                print("\n   ❌ 用户中断操作")
                return False
    
    def request_user_confirmation(self, action_description: str, element_info: Dict[str, Any] = None) -> bool:
        """
        请求用户确认操作（测试模式）- 简化版本
        
        Args:
            action_description: 操作描述
            element_info: 元素信息
            
        Returns:
            bool: 用户是否确认
        """
        if not self.test_mode:
            return True
        
        print(f"\n🧪 测试模式 - 需要用户确认操作:")
        print(f"   操作: {action_description}")
        
        if element_info:
            print(f"   元素文本: {element_info.get('text', 'N/A')}")
            print(f"   元素类型: {element_info.get('tagName', 'N/A')}")
            if element_info.get('position'):
                pos = element_info['position']
                print(f"   元素位置: ({pos.get('x', 0)}, {pos.get('y', 0)})")
        
        while True:
            try:
                response = input("   是否继续执行此操作? (y/n/s=跳过所有确认): ").strip().lower()
                if response in ['y', 'yes', '是']:
                    return True
                elif response in ['n', 'no', '否']:
                    print("   ❌ 用户取消操作")
                    return False
                elif response in ['s', 'skip', '跳过']:
                    print("   ⏭️ 跳过所有后续确认")
                    self.test_mode = False
                    return True
                else:
                    print("   请输入 y(是)/n(否)/s(跳过所有确认)")
            except KeyboardInterrupt:
                print("\n   ❌ 用户中断操作")
                return False
    
    @staticmethod
    def parse_sharepoint_url(url: str) -> Dict[str, Any]:
        """
        解析 SharePoint URL 获取路径信息
        
        Args:
            url: SharePoint URL
            
        Returns:
            Dict: 解析结果
        """
        try:
            parsed_url = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            # 提取路径信息
            path_info = {
                "site_url": f"{parsed_url.scheme}://{parsed_url.netloc}",
                "site_path": parsed_url.path,
                "query_params": query_params,
                "full_url": url
            }
            
            # 解析 id 参数中的路径
            if "id" in query_params:
                encoded_path = query_params["id"][0]
                decoded_path = urllib.parse.unquote(encoded_path)
                
                # 提取实际文件夹路径
                if "/Shared Documents/" in decoded_path:
                    folder_path = decoded_path.split("/Shared Documents/")[-1]
                    path_parts = [part for part in folder_path.split("/") if part]
                    
                    path_info.update({
                        "encoded_path": encoded_path,
                        "decoded_path": decoded_path,
                        "folder_path": folder_path,
                        "path_parts": path_parts,
                        "current_folder": path_parts[-1] if path_parts else None,
                        "parent_folders": path_parts[:-1] if len(path_parts) > 1 else []
                    })
            
            return path_info
            
        except Exception as e:
            return {
                "error": str(e),
                "full_url": url
            }
    
    def is_sharepoint_path_allowed(self, url: str) -> bool:
        """
        检查 SharePoint 路径是否在允许范围内
        
        Args:
            url: SharePoint URL
            
        Returns:
            bool: 是否允许
        """
        if not self.allowed_sharepoint_path:
            return True  # 没有限制则允许
        
        path_info = self.parse_sharepoint_url(url)
        if "error" in path_info:
            return False
        
        current_folder = path_info.get("current_folder")
        if not current_folder:
            return False
        
        # 检查当前文件夹是否在允许的路径内
        return self.allowed_sharepoint_path.lower() in current_folder.lower()
    
    def can_navigate_to_path(self, current_url: str, target_path: str) -> bool:
        """
        检查是否可以导航到目标路径
        
        Args:
            current_url: 当前 URL
            target_path: 目标路径
            
        Returns:
            bool: 是否允许导航
        """
        if not self.allowed_sharepoint_path:
            return True
        
        # 解析当前路径
        current_info = self.parse_sharepoint_url(current_url)
        if "error" in current_info:
            return False
        
        current_parts = current_info.get("path_parts", [])
        
        # 检查目标路径是否在允许范围内
        if target_path.lower() == self.allowed_sharepoint_path.lower():
            return True
        
        # 检查是否是向下级导航（允许）
        if target_path.lower() in [part.lower() for part in current_parts]:
            return True
        
        # 检查是否是向同级或下级导航
        current_folder = current_info.get("current_folder", "").lower()
        if current_folder == self.allowed_sharepoint_path.lower():
            # 在允许的根路径下，可以导航到任何子路径
            return True
        
        return False
    
    def build_sharepoint_url(self, base_url: str, target_path: str) -> str:
        """
        构建 SharePoint URL
        
        Args:
            base_url: 基础 URL
            target_path: 目标路径
            
        Returns:
            str: 构建的 URL
        """
        try:
            # 解析基础 URL
            base_info = self.parse_sharepoint_url(base_url)
            if "error" in base_info:
                return base_url
            
            # 构建新的路径
            if "Shared Documents" in base_info["decoded_path"]:
                base_path = base_info["decoded_path"].split("/Shared Documents/")[0]
                new_path = f"{base_path}/Shared Documents/{target_path}"
            else:
                new_path = f"{base_info['decoded_path']}/{target_path}"
            
            # 编码路径
            encoded_path = urllib.parse.quote(new_path, safe="")
            
            # 构建新 URL
            parsed_url = urllib.parse.urlparse(base_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            query_params["id"] = [encoded_path]
            
            new_query = urllib.parse.urlencode(query_params, doseq=True)
            new_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?{new_query}"
            
            return new_url
            
        except Exception as e:
            print(f"❌ 构建 URL 失败: {e}")
            return base_url
    
    def is_safe_action(self, action_text: str) -> bool:
        """
        检查操作是否安全
        
        Args:
            action_text: 操作按钮的文本
            
        Returns:
            bool: 是否安全
        """
        if not action_text:
            return False
        
        action_lower = action_text.lower().strip()
        
        # 检查是否在禁止列表中
        for forbidden in self.FORBIDDEN_ACTIONS:
            if forbidden.lower() in action_lower:
                return False
        
        # 检查是否在允许列表中
        for allowed in self.ALLOWED_ACTIONS:
            if allowed.lower() in action_lower:
                return True
        
        # 默认拒绝未知操作
        return False
    
    def is_safe_url(self, url: str) -> bool:
        """
        检查 URL 是否安全
        
        Args:
            url: 要检查的 URL
            
        Returns:
            bool: 是否安全
        """
        if not url:
            return False
        
        # 检查禁止的 URL 模式
        for pattern in self.FORBIDDEN_URL_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        # 检查 SharePoint 路径限制
        if not self.is_sharepoint_path_allowed(url):
            return False
        
        return True
    
    def validate_download_path(self, file_path: str) -> bool:
        """
        验证下载路径是否安全
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否安全
        """
        try:
            path = Path(file_path).resolve()
            
            # 检查是否在允许的下载目录内
            if not path.is_relative_to(self.allowed_download_path):
                return False
            
            # 检查是否包含上级目录引用
            if ".." in str(path):
                return False
            
            return True
        except Exception:
            return False
    
    def get_safe_download_path(self, filename: str) -> str:
        """
        获取安全的下载路径
        
        Args:
            filename: 文件名
            
        Returns:
            str: 安全的下载路径
        """
        # 清理文件名，移除危险字符
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        safe_filename = safe_filename.strip()
        
        # 确保文件名不为空
        if not safe_filename:
            safe_filename = "unnamed_file"
        
        # 构建完整路径
        full_path = self.allowed_download_path / safe_filename
        
        # 如果文件已存在，添加序号
        counter = 1
        original_path = full_path
        while full_path.exists():
            stem = original_path.stem
            suffix = original_path.suffix
            full_path = self.allowed_download_path / f"{stem}_{counter}{suffix}"
            counter += 1
        
        return str(full_path)
    
    def record_download(self, file_path: str) -> None:
        """
        记录已下载的文件
        
        Args:
            file_path: 文件路径
        """
        self.downloaded_files.add(file_path)
    
    def get_download_summary(self) -> Dict[str, Any]:
        """
        获取下载摘要
        
        Returns:
            Dict: 下载摘要信息
        """
        return {
            "allowed_download_path": str(self.allowed_download_path),
            "total_downloaded": len(self.downloaded_files),
            "downloaded_files": list(self.downloaded_files),
            "forbidden_actions": list(self.FORBIDDEN_ACTIONS),
            "allowed_actions": list(self.ALLOWED_ACTIONS)
        }


async def safe_download_file(
    page: Page, 
    safety_manager: SharePointSafetyManager,
    download_button_selector: str = None,
    download_button_text: str = None
) -> Optional[str]:
    """
    安全下载文件
    
    Args:
        page: 页面对象
        safety_manager: 安全管理器
        download_button_selector: 下载按钮选择器
        download_button_text: 下载按钮文本
        
    Returns:
        Optional[str]: 下载的文件路径，失败返回 None
    """
    try:
        # 检查当前 URL 是否安全
        current_url = page.url
        if not safety_manager.is_safe_url(current_url):
            print(f"❌ 当前 URL 不安全，禁止操作: {current_url}")
            return None
        
        # 查找下载按钮
        download_button = None
        
        if download_button_selector:
            try:
                download_button = page.locator(download_button_selector).first
                if await download_button.count() == 0:
                    download_button = None
            except Exception:
                download_button = None
        
        if not download_button and download_button_text:
            # 检查按钮文本是否安全
            if not safety_manager.is_safe_action(download_button_text):
                print(f"❌ 按钮操作不安全，禁止执行: {download_button_text}")
                return None
            
            try:
                download_button = page.get_by_text(download_button_text, exact=True).first
                if await download_button.count() == 0:
                    download_button = None
            except Exception:
                download_button = None
        
        if not download_button:
            print("❌ 未找到下载按钮")
            return None
        
        # 获取文件名（如果可能）
        filename = None
        try:
            # 尝试从页面获取文件名
            title_element = page.locator("h1, .ms-DetailsHeader-title, .file-name")
            if await title_element.count() > 0:
                filename = await title_element.first.inner_text()
        except Exception:
            pass
        
        if not filename:
            filename = "downloaded_file"
        
        # 获取安全的下载路径
        safe_path = safety_manager.get_safe_download_path(filename)
        
        # 设置下载路径
        await page.context.set_extra_http_headers({
            "Content-Disposition": f"attachment; filename=\"{Path(safe_path).name}\""
        })
        
        # 执行下载
        print(f"📥 开始安全下载: {filename}")
        print(f"   保存路径: {safe_path}")
        
        # 测试模式：请求用户确认下载（带悬停）
        button_text = await download_button.text_content()
        button_info = {
            "text": button_text,
            "tagName": await download_button.evaluate("el => el.tagName"),
            "position": await download_button.bounding_box()
        }
        
        # 获取按钮的选择器（用于悬停）
        button_selector = None
        if download_button_selector:
            button_selector = download_button_selector
        elif download_button_text:
            # 尝试通过文本找到选择器
            button_selector = f"text='{download_button_text}'"
        
        if not await safety_manager.request_user_confirmation_with_hover(
            page, f"下载文件 '{filename}'", button_info, button_selector
        ):
            return None
        
        # 点击下载按钮
        await download_button.click()
        
        # 等待下载完成
        await page.wait_for_timeout(3000)
        
        # 记录下载
        safety_manager.record_download(safe_path)
        
        print(f"✅ 文件下载完成: {safe_path}")
        return safe_path
        
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return None


async def safe_click_element_with_confirmation(
    page: Page,
    safety_manager: SharePointSafetyManager,
    element_selector: str,
    action_description: str = None,
    element_text: str = None
) -> bool:
    """
    安全点击元素（带测试模式确认）
    
    Args:
        page: 页面对象
        safety_manager: 安全管理器
        element_selector: 元素选择器
        action_description: 操作描述
        element_text: 元素文本（用于验证）
        
    Returns:
        bool: 是否成功点击
    """
    try:
        # 等待元素出现
        element = await page.wait_for_selector(element_selector, timeout=10000)
        if not element:
            print(f"❌ 未找到元素: {element_selector}")
            return False
        
        # 获取元素信息
        actual_text = await element.text_content()
        element_info = {
            "text": actual_text,
            "tagName": await element.evaluate("el => el.tagName"),
            "position": await element.bounding_box()
        }
        
        if element_text and element_text not in actual_text:
            print(f"⚠️ 元素文本不匹配: 期望 '{element_text}', 实际 '{actual_text}'")
            return False
        
        # 检查操作是否安全
        if not safety_manager.is_safe_action(actual_text):
            print(f"❌ 不安全的操作: {actual_text}")
            return False
        
        # 测试模式：请求用户确认（带悬停）
        action_desc = action_description or f"点击元素 '{actual_text}'"
        if not await safety_manager.request_user_confirmation_with_hover(
            page, action_desc, element_info, element_selector
        ):
            return False
        
        # 点击元素
        await element.click()
        print(f"✅ 安全点击元素: {actual_text}")
        return True
        
    except Exception as e:
        print(f"❌ 点击元素失败: {e}")
        return False


async def safe_navigate_to_file(
    page: Page,
    safety_manager: SharePointSafetyManager,
    file_url: str
) -> bool:
    """
    安全导航到文件页面
    
    Args:
        page: 页面对象
        safety_manager: 安全管理器
        file_url: 文件 URL
        
    Returns:
        bool: 是否成功
    """
    try:
        # 检查 URL 是否安全
        if not safety_manager.is_safe_url(file_url):
            print(f"❌ 文件 URL 不安全，禁止访问: {file_url}")
            return False
        
        # 导航到文件页面
        await page.goto(file_url, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")
        
        # 更新当前路径
        safety_manager.current_sharepoint_path = file_url
        
        print(f"✅ 安全导航到文件页面: {file_url}")
        return True
        
    except Exception as e:
        print(f"❌ 导航失败: {e}")
        return False


async def safe_navigate_to_folder(
    page: Page,
    safety_manager: SharePointSafetyManager,
    target_folder: str
) -> bool:
    """
    安全导航到指定文件夹
    
    Args:
        page: 页面对象
        safety_manager: 安全管理器
        target_folder: 目标文件夹名称
        
    Returns:
        bool: 是否成功
    """
    try:
        current_url = page.url
        
        # 检查是否可以导航到目标路径
        if not safety_manager.can_navigate_to_path(current_url, target_folder):
            print(f"❌ 禁止导航到路径: {target_folder}")
            return False
        
        # 构建新的 URL
        new_url = safety_manager.build_sharepoint_url(current_url, target_folder)
        
        # 检查新 URL 是否安全
        if not safety_manager.is_safe_url(new_url):
            print(f"❌ 目标 URL 不安全: {new_url}")
            return False
        
        # 测试模式：请求用户确认导航
        if not safety_manager.request_user_confirmation(f"导航到文件夹 '{target_folder}'", {"url": new_url}):
            return False
        
        # 导航到新页面
        await page.goto(new_url, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")
        
        # 更新当前路径
        safety_manager.current_sharepoint_path = new_url
        
        print(f"✅ 安全导航到文件夹: {target_folder}")
        print(f"   新 URL: {new_url}")
        return True
        
    except Exception as e:
        print(f"❌ 导航失败: {e}")
        return False


async def scan_page_for_safe_actions(
    page: Page,
    safety_manager: SharePointSafetyManager
) -> Dict[str, Any]:
    """
    扫描页面中的安全操作
    
    Args:
        page: 页面对象
        safety_manager: 安全管理器
        
    Returns:
        Dict: 扫描结果
    """
    try:
        # 获取所有按钮和链接
        buttons = await page.evaluate("""
            () => {
                const elements = [];
                const allElements = document.querySelectorAll('button, a, [role="button"], [onclick]');
                
                allElements.forEach((el, index) => {
                    const rect = el.getBoundingClientRect();
                    const style = getComputedStyle(el);
                    
                    if (rect.width > 0 && rect.height > 0 && 
                        style.visibility !== 'hidden' && 
                        style.display !== 'none') {
                        
                        const text = (el.textContent || "").trim();
                        const href = el.href || "";
                        const onclick = el.getAttribute('onclick') || "";
                        
                        if (text || href || onclick) {
                            elements.push({
                                index: index,
                                tagName: el.tagName.toLowerCase(),
                                text: text,
                                href: href,
                                onclick: onclick,
                                id: el.id || null,
                                className: el.className || null,
                                position: {
                                    x: Math.round(rect.x),
                                    y: Math.round(rect.y),
                                    width: Math.round(rect.width),
                                    height: Math.round(rect.height)
                                }
                            });
                        }
                    }
                });
                
                return elements;
            }
        """)
        
        # 分析操作安全性
        safe_actions = []
        unsafe_actions = []
        
        for button in buttons:
            action_info = {
                "index": button["index"],
                "tagName": button["tagName"],
                "text": button["text"],
                "href": button["href"],
                "onclick": button["onclick"],
                "position": button["position"]
            }
            
            # 检查操作是否安全
            is_safe = (
                safety_manager.is_safe_action(button["text"]) and
                safety_manager.is_safe_url(button["href"]) and
                not button["onclick"] or "download" in button["onclick"].lower()
            )
            
            if is_safe:
                safe_actions.append(action_info)
            else:
                unsafe_actions.append(action_info)
        
        return {
            "total_actions": len(buttons),
            "safe_actions": safe_actions,
            "unsafe_actions": unsafe_actions,
            "safe_count": len(safe_actions),
            "unsafe_count": len(unsafe_actions)
        }
        
    except Exception as e:
        print(f"❌ 扫描页面操作失败: {e}")
        return {
            "total_actions": 0,
            "safe_actions": [],
            "unsafe_actions": [],
            "safe_count": 0,
            "unsafe_count": 0,
            "error": str(e)
        }
