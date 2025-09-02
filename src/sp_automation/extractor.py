from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Literal
from playwright.async_api import Page

# 中文注释：通用网页抽取模块（对应“新增通用网页抽取模块（基于选择器与Schema）”）
# 设计目标：
# - 基于 CSS/XPath 选择器定义字段
# - 支持提取文本、属性、inner_html
# - 支持列表抽取（对多个元素映射子规则）

SelectorType = Literal["css", "xpath"]
ValueType = Literal["text", "attr", "html"]


@dataclass
class FieldRule:
    name: str                      # 中文：字段名
    selector: str                  # 中文：选择器（CSS 或 XPath）
    selector_type: SelectorType = "css"
    value_type: ValueType = "text" # 中文：提取类型
    attr: Optional[str] = None     # 中文：当 value_type=attr 时需要
    first: bool = True             # 中文：是否只取第一个
    required: bool = False         # 中文：是否必填（缺失则返回 None 或报错，默认不报错）


@dataclass
class ListRule:
    name: str
    item_selector: str             # 中文：列表项容器选择器
    selector_type: SelectorType = "css"
    fields: List[FieldRule] = None # 中文：对子项应用的字段规则


@dataclass
class ExtractSchema:
    fields: List[FieldRule]
    lists: List[ListRule]


async def extract_fields(page: Page, fields: List[FieldRule]) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    for rule in fields:
        try:
            if rule.selector_type == "css":
                locator = page.locator(rule.selector)
            else:
                locator = page.locator(f'xpath={rule.selector}')

            count = await locator.count()
            if count == 0:
                data[rule.name] = None
                continue

            target = locator.first if rule.first else locator

            if rule.value_type == "text":
                value = await target.inner_text()
            elif rule.value_type == "html":
                value = await target.inner_html()
            elif rule.value_type == "attr" and rule.attr:
                value = await target.get_attribute(rule.attr)
            else:
                value = None

            data[rule.name] = value
        except Exception:
            data[rule.name] = None
    return data


async def extract_list(page: Page, list_rule: ListRule) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    try:
        locator = page.locator(list_rule.item_selector) if list_rule.selector_type == "css" else page.locator(f'xpath={list_rule.item_selector}')
        count = await locator.count()
        for i in range(count):
            row = locator.nth(i)
            row_data: Dict[str, Any] = {}
            for f in (list_rule.fields or []):
                try:
                    sub = row.locator(f.selector) if f.selector_type == "css" else row.locator(f'xpath={f.selector}')
                    target = sub.first if f.first else sub
                    if f.value_type == "text":
                        value = await target.inner_text()
                    elif f.value_type == "html":
                        value = await target.inner_html()
                    elif f.value_type == "attr" and f.attr:
                        value = await target.get_attribute(f.attr)
                    else:
                        value = None
                    row_data[f.name] = value
                except Exception:
                    row_data[f.name] = None
            items.append(row_data)
    except Exception:
        return []
    return items


async def extract_by_schema(page: Page, schema: ExtractSchema) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    result.update(await extract_fields(page, schema.fields or []))
    for lst in (schema.lists or []):
        result[lst.name] = await extract_list(page, lst)
    return result
