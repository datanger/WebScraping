from typing import Dict, Any
from playwright.async_api import BrowserContext
from .sharepoint import goto_sharepoint_library, extract_text


async def scrape_library_title(context: BrowserContext, library_url: str) -> Dict[str, Any]:
    """
    中文注释：示例抓取函数（对应“基于持久化会话的抓取运行脚本”将调用）。
    - 进入文档库后抓取页面标题与部分正文文本
    - 后续可扩展：列表项遍历、下载链接抽取等
    """
    page = await goto_sharepoint_library(context, library_url)
    title = await page.title()
    body_sample = await extract_text(page, "body")
    return {
        "title": title,
        "body_sample": (body_sample or "")[:1000],
        "url": library_url,
    }
