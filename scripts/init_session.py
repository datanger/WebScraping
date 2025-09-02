import asyncio
from sp_automation.session import init_and_save_session
from sp_automation.config import settings

# 中文注释：对应计划——实现会话初始化脚本（人工双重登录后保存会话）


async def main() -> None:
    await init_and_save_session(start_url=settings.target_url, storage_file=settings.storage_state_file, headless=False)


if __name__ == "__main__":
    asyncio.run(main())
