import os
import json
import time
from typing import Optional
from playwright.async_api import Page
from .browser import create_context, close_all
from .config import settings
from .otp_providers import get_otp_from_provider


async def init_and_save_session(start_url: Optional[str] = None, storage_file: Optional[str] = None, headless: Optional[bool] = None) -> None:
    """
    中文注释：初始化并持久化会话（对应“实现会话初始化脚本”）。
    - 自动尝试 OTP（TOTP/IMAP）；若未配置或失败，则提示人工输入验证码
    - 第一次运行建议 headless=False，便于手动通过双重登录/MFA
    - 登录完成后保存 storage_state 到文件，供后续无人值守脚本复用
    """
    start_url = start_url or settings.target_url
    storage_file = storage_file or settings.storage_state_file

    pw, browser, context = await create_context(headless=False if headless is None else headless)
    page = await context.new_page()

    await page.goto(start_url, wait_until="domcontentloaded")

    # 中文注释：自动化尝试处理验证码（若页面流程符合标准 AAD/公司 IdP 界面）
    await _try_handle_mfa(page)

    # 中文注释：等待用户完成其余登录流程或手动输入验证码
    _print_instructions(storage_file)
    await _wait_user_confirm(page)

    _ensure_dir(os.path.dirname(storage_file))
    await context.storage_state(path=storage_file)

    await close_all(pw, browser)


async def _try_handle_mfa(page: Page) -> None:
    # 中文注释：尝试识别常见验证码输入框并自动填入
    try:
        otp = get_otp_from_provider()
        if not otp:
            return
        # 常见 AAD/公司 IdP 可能的验证码输入选择器（可按实际定制）
        selectors = [
            'input[name="otc"]',
            'input[name="code"]',
            'input[autocomplete="one-time-code"]',
            'input[type="tel"]',
            'input[type="text"]',
        ]
        for sel in selectors:
            loc = page.locator(sel)
            if await loc.count() > 0:
                try:
                    await loc.first.fill(otp)
                    # 可能存在“验证/下一步”按钮
                    for btn_txt in ["验证", "下一步", "Next", "Verify", "Continue"]:
                        btn = page.get_by_role("button", name=btn_txt)
                        if await btn.count() > 0:
                            await btn.first.click()
                            break
                    break
                except Exception:
                    continue
    except Exception:
        pass


def _print_instructions(storage_file: str) -> None:
    print("如页面仍需交互，请在浏览器中完成登录或输入验证码。完成后回到终端按回车，保存会话到：", storage_file)


async def _wait_user_confirm(page: Page) -> None:
    try:
        input("当你确认已成功进入 SharePoint 目标站点后，按回车继续...")
    except EOFError:
        await page.wait_for_load_state("networkidle")


def _ensure_dir(path: str) -> None:
    if not path:
        return
    os.makedirs(path, exist_ok=True)


async def save_session_state(context, session_file: Optional[str] = None) -> None:
    """
    保存会话状态到文件
    借鉴自 persistent_session_manager.py 的会话保存功能
    """
    session_file = session_file or settings.storage_state_file
    
    try:
        # 获取所有cookies
        cookies = await context.cookies()
        
        # 保存到文件
        session_data = {
            "timestamp": time.time(),
            "cookies": cookies,
            "profile_dir": getattr(settings, 'user_data_dir', None)
        }
        
        _ensure_dir(os.path.dirname(session_file))
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
            
        print(f"💾 会话状态已保存到: {session_file}")
        
    except Exception as e:
        print(f"❌ 保存会话状态失败: {e}")


async def restore_session_state(context, session_file: Optional[str] = None) -> None:
    """
    从文件恢复会话状态
    借鉴自 persistent_session_manager.py 的会话恢复功能
    """
    session_file = session_file or settings.storage_state_file
    
    try:
        if not os.path.exists(session_file):
            print("📝 未找到保存的会话状态，将使用新的会话")
            return
            
        with open(session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
            
        cookies = session_data.get('cookies', [])
        if cookies:
            # 恢复cookies到浏览器
            await context.add_cookies(cookies)
            print(f"🔄 已恢复 {len(cookies)} 个cookies")
        else:
            print("📝 未找到有效的cookies")
            
    except Exception as e:
        print(f"❌ 恢复会话状态失败: {e}")


async def init_persistent_session(
    start_url: Optional[str] = None, 
    storage_file: Optional[str] = None, 
    headless: Optional[bool] = None,
    browser_type: str = "chromium"
) -> tuple:
    """
    初始化持久化会话
    借鉴自三个脚本的持久化会话管理功能
    """
    start_url = start_url or settings.target_url
    storage_file = storage_file or settings.storage_state_file
    
    # 使用持久化模式创建上下文
    pw, browser, context = await create_context(
        headless=headless,
        browser_type=browser_type,
        persistent=settings.persistent_mode,
        user_data_dir=settings.user_data_dir if settings.persistent_mode else None
    )
    
    # 恢复会话状态
    await restore_session_state(context, storage_file)
    
    return pw, browser, context
