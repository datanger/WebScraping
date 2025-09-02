import argparse
import asyncio
import json
from pathlib import Path
from typing import Any, Dict

from sp_automation.browser import create_context, close_all
from sp_automation.extractor import ExtractSchema, FieldRule, ListRule, extract_by_schema

# 中文注释：命令行抽取脚本（对应“新增命令行脚本运行抽取”）


def load_schema(path: str) -> ExtractSchema:
    data: Dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    fields = [FieldRule(**f) for f in data.get("fields", [])]
    lists = [ListRule(name=l["name"], item_selector=l["item_selector"], selector_type=l.get("selector_type", "css"), fields=[FieldRule(**f) for f in l.get("fields", [])]) for l in data.get("lists", [])]
    return ExtractSchema(fields=fields, lists=lists)


async def run(url: str, schema_path: str, out: str) -> None:
    schema = load_schema(schema_path)
    pw, browser, context = await create_context(headless=True)
    try:
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")
        result = await extract_by_schema(page, schema)
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写出: {out}")
    finally:
        await close_all(pw, browser)


def main() -> None:
    parser = argparse.ArgumentParser(description="基于选择器Schema的网页抽取")
    parser.add_argument("url", help="目标URL")
    parser.add_argument("schema", help="抽取规则JSON文件路径")
    parser.add_argument("--out", default="output/result.json", help="输出JSON文件路径")
    args = parser.parse_args()
    asyncio.run(run(args.url, args.schema, args.out))


if __name__ == "__main__":
    main()
