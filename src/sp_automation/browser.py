from typing import Optional, Tuple, Literal
from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext
from .config import settings

BrowserType = Literal["chromium", "edge", "firefox"]


async def create_context(
    headless: Optional[bool] = None,
    storage_state_file: Optional[str] = None,
    proxy: Optional[str] = None,
    slow_mo_ms: Optional[int] = None,
    browser_type: BrowserType = "chromium",
    persistent: bool = False,
    user_data_dir: Optional[str] = None,
) -> Tuple[Playwright, Browser, BrowserContext]:
    """
    中文注释：创建浏览器上下文（增强版）。
    - 支持多种浏览器类型（chromium/edge/firefox）
    - 支持持久化上下文模式
    - 支持 headless/slowmo/proxy
    - 可加载持久化的 storage_state（复用已通过双重登录的会话）
    """
    headless = settings.headless if headless is None else headless
    slow_mo_ms = settings.slow_mo_ms if slow_mo_ms is None else slow_mo_ms
    storage_state = storage_state_file or settings.storage_state_file

    pw = await async_playwright().start()

    # 选择浏览器引擎
    if browser_type == "edge":
        browser_engine = pw.chromium
        channel = "msedge"
    elif browser_type == "firefox":
        browser_engine = pw.firefox
        channel = None
    else:
        browser_engine = pw.chromium
        channel = None

    # 基础启动参数
    launch_args = {"headless": headless}
    if proxy or settings.proxy:
        launch_args["proxy"] = {"server": proxy or settings.proxy}
    if channel:
        launch_args["channel"] = channel

    # 反检测参数
    if browser_type in ["chromium", "edge"]:
        launch_args.setdefault("args", []).extend([
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--no-first-run",
            "--no-default-browser-check",
        ])

    if persistent and user_data_dir:
        # 持久化上下文模式
        context_args = {
            "user_data_dir": user_data_dir,
            "ignore_https_errors": True,
            "java_script_enabled": True,
            "timezone_id": "UTC",
            "locale": "zh-CN",
            "reduced_motion": "reduce",
            "bypass_csp": True,
            "slow_mo": slow_mo_ms or 0,
            "accept_downloads": True,
        }
        
        context = await browser_engine.launch_persistent_context(**{**launch_args, **context_args})
        browser = context  # 持久化模式下，context 就是 browser
        
        # 隐藏 webdriver 特征
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
    else:
        # 普通上下文模式
        browser = await browser_engine.launch(**launch_args)
        
        context_args = {
            "storage_state": storage_state if storage_state and _file_exists(storage_state) else None,
            "ignore_https_errors": True,
            "java_script_enabled": True,
            "timezone_id": "UTC",
            "locale": "zh-CN",
            "reduced_motion": "reduce",
            "bypass_csp": True,
            "accept_downloads": True,
        }

        context = await browser.new_context(**{k: v for k, v in context_args.items() if v is not None})

    # 设置默认超时
    context.set_default_timeout(settings.default_timeout_ms)
    return pw, browser, context


async def close_all(pw: Playwright, browser: Browser) -> None:
    """中文注释：关闭浏览器与 Playwright 实例。"""
    await browser.close()
    await pw.stop()


def _file_exists(path: str) -> bool:
    try:
        import os
        return os.path.isfile(path)
    except Exception:
        return False
