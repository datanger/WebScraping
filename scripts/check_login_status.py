#!/usr/bin/env python3
"""
检查当前浏览器登录状态（独立脚本）

用法:
  仅检测（不启动调试浏览器）：
    python scripts/check_login_status.py

  指定目标地址：
    python scripts/check_login_status.py --url https://your.sharepoint.com/sites/YourSite

  确保登录（必要时引导启动 scripts/start_debug_browser.py 并复检）：
    python scripts/check_login_status.py --ensure
"""

import argparse
import asyncio
import sys

sys.path.append('.')

from src.sp_automation.login_status_detector import LoginStatusDetector, LoginPageStatus
from src.sp_automation.config import settings


async def main_async(args: argparse.Namespace) -> int:
    detector = LoginStatusDetector()
    target_url = args.url or settings.target_url

    if args.ensure:
        status = await detector.ensure_logged_in(target_url)
    else:
        status = await detector.open_target_and_detect(target_url)

    print(f"登录状态: {status}")

    # 退出码约定：0=已登录，1=需要登录/未知
    return 0 if status == LoginPageStatus.logged_in else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="检查当前浏览器登录状态")
    parser.add_argument("--url", dest="url", default=None, help="目标地址（默认读取 .env 中的 SP_TARGET_URL）")
    parser.add_argument("--ensure", action="store_true", help="必要时引导登录并复检")
    args = parser.parse_args()

    exit_code = asyncio.run(main_async(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()


