import asyncio
from sp_automation.browser import create_context, close_all
from sp_automation.config import settings
from sp_automation.scraping import scrape_library_title

# 中文注释：对应计划——实现基于持久化会话的抓取运行脚本


async def main() -> None:
    pw, browser, context = await create_context(headless=True)
    try:
        result = await scrape_library_title(context, settings.target_url)
        print(result)
    finally:
        await close_all(pw, browser)


if __name__ == "__main__":
    asyncio.run(main())
