from typing import Optional
from playwright.async_api import BrowserContext, Page

# 中文注释：SharePoint 导航与常用操作模块
# 对应计划：后续抓取模块会调用这些方法进行页面进入与元素等待


async def goto_sharepoint_library(context: BrowserContext, library_url: str) -> Page:
    """
    中文注释：打开指定文档库页面，并等待前端加载完成。
    对应计划：SharePoint 导航
    """
    page = await context.new_page()
    await page.goto(library_url, wait_until="domcontentloaded")
    await page.wait_for_load_state("networkidle")
    return page


async def extract_text(page: Page, selector: str) -> Optional[str]:
    """中文注释：通用纯文本抽取。"""
    try:
        loc = page.locator(selector)
        await loc.first.wait_for(state="visible", timeout=15000)
        return await loc.first.inner_text()
    except Exception:
        return None


async def click_by_text(page: Page, text: str) -> None:
    """中文注释：通过可见文本点击（适配 SharePoint React 组件）。"""
    btn = page.get_by_text(text, exact=True)
    await btn.first.click()
