from typing import Optional, Tuple
from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext
from .config import settings


async def create_context(
    headless: Optional[bool] = None,
    storage_state_file: Optional[str] = None,
    proxy: Optional[str] = None,
    slow_mo_ms: Optional[int] = None,
) -> Tuple[Playwright, Browser, BrowserContext]:
    """
    中文注释：创建浏览器上下文（对应“浏览器封装”）。
    - 支持 headless/slowmo/proxy
    - 可加载持久化的 storage_state（复用已通过双重登录的会话）
    """
    headless = settings.headless if headless is None else headless
    slow_mo_ms = settings.slow_mo_ms if slow_mo_ms is None else slow_mo_ms
    storage_state = storage_state_file or settings.storage_state_file

    pw = await async_playwright().start()

    launch_args = {"headless": headless}
    if proxy or settings.proxy:
        launch_args["proxy"] = {"server": proxy or settings.proxy}

    browser = await pw.chromium.launch(**launch_args)

    context_args = {
        "storage_state": storage_state if storage_state and _file_exists(storage_state) else None,
        "ignore_https_errors": True,
        "java_script_enabled": True,
        "timezone_id": "UTC",
        "locale": "zh-CN",
        "reduced_motion": "reduce",
        "bypass_csp": True,
        "record_video_dir": None,
        "record_har_path": None,
        "slow_mo": slow_mo_ms or 0,
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
