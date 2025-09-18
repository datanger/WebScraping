"""
Login status detector

Implements the flow described in `浏览器登陆状态检测.md`:
- Detect when a debug-browser is available via CDP
- Open target URL in existing browser and determine whether login is required
- Provide helper to launch the debug browser starter script when needed

This module is intentionally framework-light and exposes async helpers that
scripts can call at appropriate trigger points (e.g., repeated failures or
global zero download speed).
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import http.client

from playwright.async_api import async_playwright, BrowserContext, Page

from .config import settings


class LoginPageStatus(str, Enum):
    logged_in = "logged_in"
    login_required = "login_required"
    unknown = "unknown"


@dataclass
class LoginCheckConfig:
    debug_port: int = int(os.getenv("DEBUG_PORT", "9222"))
    target_url: str = settings.target_url


class LoginStatusDetector:
    def __init__(self, config: Optional[LoginCheckConfig] = None) -> None:
        self.config = config or LoginCheckConfig()

    def _fetch_cdp_json(self, path: str) -> Optional[dict]:
        try:
            conn = http.client.HTTPConnection("127.0.0.1", self.config.debug_port, timeout=2)
            conn.request("GET", path)
            resp = conn.getresponse()
            if resp.status == 200:
                data = resp.read().decode("utf-8", errors="ignore")
                return json.loads(data)
        except Exception:
            return None
        finally:
            try:
                conn.close()
            except Exception:
                pass
        return None

    def is_cdp_browser_running(self) -> bool:
        """Check if a browser with remote debugging is running on the port."""
        data = self._fetch_cdp_json("/json/version")
        return bool(data and data.get("Browser"))

    async def _connect_over_cdp(self):
        return await async_playwright().start()

    async def open_target_and_detect(self, target_url: Optional[str] = None) -> LoginPageStatus:
        """Connect to existing debug browser, open target URL and detect login status."""
        url = target_url or self.config.target_url
        if not url:
            return LoginPageStatus.unknown

        if not self.is_cdp_browser_running():
            return LoginPageStatus.unknown

        pw = await async_playwright().start()
        try:
            endpoint = f"http://127.0.0.1:{self.config.debug_port}"
            browser = await pw.chromium.connect_over_cdp(endpoint)
            # Reuse existing context when possible
            contexts = browser.contexts
            context: BrowserContext = contexts[0] if contexts else await browser.new_context()
            page: Page = context.pages[0] if context.pages else await context.new_page()

            await page.goto(url, wait_until="domcontentloaded")

            # Heuristics to detect Microsoft/SharePoint login page
            page_url = page.url.lower()
            title = (await page.title()).lower() if page else ""
            login_inputs = await page.locator("input[name='loginfmt'], input[type='email'], input[type='password']").count()

            if ("login.microsoftonline" in page_url) or ("/login" in page_url) or ("signin" in page_url) or (login_inputs > 0) or ("sign in" in title) or ("登录" in title):
                # 尝试脚本化点击包含特定字符串的按钮（例如 @kotei.com.cn）
                try:
                    click_text = os.getenv("LOGIN_CLICK_TEXT", "@kotei.com.cn")
                    if click_text:
                        # 优先尝试严格文本匹配
                        locator = page.get_by_text(click_text, exact=False)
                        if await locator.count() == 0:
                            # 回退到常见可点击元素筛选
                            locator = page.locator(
                                f"button:has-text(\"{click_text}\"), a:has-text(\"{click_text}\"), div:has-text(\"{click_text}\")"
                            )
                        if await locator.count() > 0:
                            await locator.first.click(timeout=3000)
                            # 等待页面变化
                            try:
                                await page.wait_for_load_state("networkidle", timeout=5000)
                            except Exception:
                                pass
                            # 重新评估登录状态
                            page_url = page.url.lower()
                            title = (await page.title()).lower() if page else ""
                            login_inputs = await page.locator("input[name='loginfmt'], input[type='email'], input[type='password']").count()
                            if not (("login.microsoftonline" in page_url) or ("/login" in page_url) or ("signin" in page_url) or (login_inputs > 0) or ("sign in" in title) or ("登录" in title)):
                                # 再检查是否已进入文档库
                                list_loc = page.locator("div.Files, div#appRoot, div#spoAppComponent")
                                if await list_loc.count() > 0:
                                    return LoginPageStatus.logged_in
                except Exception:
                    pass
                return LoginPageStatus.login_required

            # Heuristic for doc library presence
            list_loc = page.locator("div.Files, div#appRoot, div#spoAppComponent")
            try:
                if await list_loc.count() > 0:
                    return LoginPageStatus.logged_in
            except Exception:
                pass

            return LoginPageStatus.unknown
        finally:
            try:
                await pw.stop()
            except Exception:
                pass

    async def ensure_logged_in(self, target_url: Optional[str] = None) -> LoginPageStatus:
        """Main orchestration:
        - If debug browser exists, open target URL and check status
        - If login required or no browser, prompt to start debug browser script and wait
        - Return final detected status (best effort)
        """
        status = await self.open_target_and_detect(target_url)
        if status == LoginPageStatus.logged_in:
            return status

        # Start debug browser script to allow manual login
        script_path = os.path.join("scripts", "start_debug_browser.py")
        if os.path.exists(script_path):
            print("🔑 需要登录，启动调试浏览器脚本以完成登录...")
            env = dict(os.environ)
            env["AUTO_CONTINUE"] = "1"  # 非交互模式
            try:
                # 后台启动，携带目标地址让浏览器直接打开
                env["TARGET_URL"] = target_url or self.config.target_url
                subprocess.Popen([sys.executable if "sys" in globals() else "python", script_path], env=env)
            except Exception:
                os.system(f"AUTO_CONTINUE=1 python {script_path} &")
        else:
            print("⚠️ 未找到 scripts/start_debug_browser.py，请手动启动带调试端口的浏览器并登录。")

        # 给浏览器一些时间初始化
        await asyncio.sleep(2)
        # 直接打开目标地址并复检
        return await self.open_target_and_detect(target_url)


