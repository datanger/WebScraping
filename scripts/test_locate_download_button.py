#!/usr/bin/env python3
"""
基于 zip_traverse_stream_*.log 的定位测试：
1) 读取日志中的 file_name/path/page_url/href
2) 连接已有浏览器（9222），直达 page_url
3) 在 grid 列表内滚动检索该文件行
4) 右键打开菜单并尝试定位“下载/Download”菜单项

仅用于定位验证，不触发真正下载。
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.append('.')
from playwright.async_api import async_playwright
from src.sp_automation.sharepoint_scanner import SharePointScanner


async def read_first_entry_from_log(log_path: Path) -> dict:
    if not log_path.exists():
        raise FileNotFoundError(f"日志不存在: {log_path}")
    # 允许 .log(一行一条JSON) 或 .json(数组)
    if log_path.suffix == '.json':
        data = json.loads(log_path.read_text(encoding='utf-8') or '[]')
        if isinstance(data, list) and data:
            return data[0]
        elif isinstance(data, dict):
            return data
        raise ValueError('JSON 日志为空或格式不正确')
    else:
        # 读取第一行 JSON
        with log_path.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    return json.loads(line)
                except Exception:
                    continue
        raise ValueError('LOG 文件没有有效的 JSON 行')


async def locate_row_and_menu(page, file_name: str) -> bool:
    # 选择器集合
    row_selectors = [
        "[role='grid'] div[data-automation-id='DetailsRow']",
        "[role='grid'] .ms-DetailsRow",
        "div[role='row'].ms-DetailsRow",
    ]
    name_cell_selector = "span.field-LinkFilename-htmlGrid_1, a[role='link'], a.ms-Link, span[title]"
    list_surface = page.locator("[role='grid'] .ms-List-surface, [role='grid'] .ms-DetailsList")

    # 滚动查找该文件行
    target_row = None
    for _ in range(30):
        for row_sel in row_selectors:
            # 使用 ends-with 策略减小前缀干扰
            rows = page.locator(row_sel).filter(has_text=file_name)
            if await rows.count() > 0:
                # 精确筛选名称单元格文本末尾匹配
                candidate = rows.first
                name_cell = candidate.locator(name_cell_selector)
                if await name_cell.count() > 0:
                    # 进一步校验文本
                    texts = [t.strip() for t in (await name_cell.all_inner_texts())]
                    if any(t.endswith(file_name) for t in texts):
                        target_row = candidate
                        break
                else:
                    # 无名称单元格时，直接使用该行
                    target_row = candidate
                    break
        if target_row is not None:
            break
        # 滚动列表容器加载更多
        try:
            if await list_surface.count() > 0:
                await list_surface.evaluate("el => el.scrollBy(0, el.clientHeight)")
            else:
                await page.evaluate("window.scrollBy(0, document.body.scrollHeight/1.5)")
        except Exception:
            pass
        await page.wait_for_timeout(250)

    if target_row is None:
        print(f"❌ 未在当前页的grid中找到目标文件行: {file_name}")
        return False

    await target_row.scroll_into_view_if_needed()
    clickable = target_row.locator(name_cell_selector)
    if await clickable.count() == 0:
        clickable = target_row

    # 右键打开菜单
    try:
        await clickable.click(button='right', timeout=8000)
        await page.wait_for_timeout(300)
    except Exception as e:
        print(f"❌ 右键失败: {e}")
        return False

    # 定位“下载/Download”菜单项
    candidates = [
        page.locator("role=menuitem[name='下载']"),
        page.get_by_role('menuitem', name='下载'),
        page.get_by_text('下载', exact=False),
        page.get_by_text('Download', exact=False),
        page.locator("button:has-text('下载')"),
    ]
    for cand in candidates:
        try:
            if await cand.count() > 0:
                box = await cand.bounding_box()
                print(f"✅ 找到下载按钮，位置: {box}")
                return True
        except Exception:
            continue

    print("❌ 未找到下载按钮(菜单项)")
    return False


async def main():
    # 解析参数：日志路径（可选，不传则取 downloads/logs 下最新 zip_traverse_stream_*.log 或 zip_traverse_*.json）
    log_path = None
    if len(sys.argv) > 1:
        log_path = Path(sys.argv[1])
    else:
        logs_dir = Path('downloads/logs')
        candidates = sorted(list(logs_dir.glob('zip_traverse_stream_*.log')) + list(logs_dir.glob('zip_traverse_*.json')))
        if not candidates:
            print('❌ 未找到 zip 遍历日志，请先运行批量扫描生成日志')
            return
        log_path = candidates[-1]

    entry = await read_first_entry_from_log(log_path)
    file_name = entry.get('text')
    page_url = entry.get('page_url')
    if not file_name or not page_url:
        print(f"❌ 日志记录缺少必要字段 text/page_url: {entry}")
        return

    print(f"📄 测试文件: {file_name}")
    print(f"🔗 目标页: {page_url}")

    playwright = await async_playwright().start()
    scanner = SharePointScanner(test_mode=False, debug_port=9222)
    try:
        ok = await scanner.connect_to_browser(playwright)
        if not ok:
            print('❌ 无法连接到现有浏览器(9222)')
            return
        # 复用现有 SharePoint 标签页，或新开
        ctx = scanner.context
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto(page_url)
        try:
            await page.wait_for_load_state('domcontentloaded', timeout=10000)
        except Exception:
            pass
        await page.wait_for_timeout(500)

        found = await locate_row_and_menu(page, file_name)
        if found:
            print('✅ 成功定位到下载按钮(仅定位，不点击)')
        else:
            print('❌ 未能定位到下载按钮')
    finally:
        await scanner.cleanup_pages()
        await scanner.disconnect()
        await playwright.stop()


if __name__ == '__main__':
    asyncio.run(main())


