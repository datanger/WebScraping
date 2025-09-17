from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from playwright.async_api import Page


@dataclass
class ElementInfo:
    """页面元素信息"""
    index: int
    tag_name: str
    text: str
    id: Optional[str]
    class_name: Optional[str]
    visible: bool
    clickable: bool
    position: Dict[str, int]  # x, y, width, height
    attributes: Dict[str, Any]
    styles: Dict[str, str]


@dataclass
class ButtonDetectionResult:
    """按钮检测结果"""
    page_info: Dict[str, Any]
    buttons: List[ElementInfo]
    statistics: Dict[str, int]


async def detect_buttons_on_page(page: Page) -> ButtonDetectionResult:
    """
    检测页面上的所有按钮元素
    借鉴自 persistent_session_manager.py 的按钮检测功能
    """
    print("🔍 检测页面按钮...")
    
    result = await page.evaluate("""
        () => {
            const getButtonInfo = (element, type, index) => {
                const rect = element.getBoundingClientRect();
                const style = getComputedStyle(element);
                
                return {
                    type: type,
                    index: index,
                    tagName: element.tagName.toLowerCase(),
                    text: (element.textContent || "").trim(),
                    id: element.id || null,
                    className: element.className || null,
                    visible: rect.width > 0 && rect.height > 0 && 
                            style.visibility !== 'hidden' && 
                            style.display !== 'none',
                    clickable: !element.disabled,
                    position: {
                        x: Math.round(rect.x),
                        y: Math.round(rect.y),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height)
                    },
                    attributes: getAttributes(element, type),
                    styles: {
                        backgroundColor: style.backgroundColor,
                        color: style.color,
                        fontSize: style.fontSize,
                        display: style.display,
                        cursor: style.cursor
                    }
                };
            };
            
            const getAttributes = (element, type) => {
                switch(type) {
                    case 'button_tag':
                        return {
                            type: element.type || 'button',
                            disabled: !!element.disabled,
                            role: element.getAttribute('role') || null,
                            'aria-label': element.getAttribute('aria-label') || null
                        };
                    case 'input_button':
                        return {
                            type: element.type,
                            value: element.value,
                            disabled: !!element.disabled
                        };
                    case 'role_button':
                        return {
                            role: 'button',
                            ariaLabel: element.getAttribute('aria-label') || null
                        };
                    case 'onclick_element':
                        return {
                            onclick: element.getAttribute('onclick')
                        };
                    case 'clickable_link':
                        return {
                            href: element.href,
                            target: element.target || null
                        };
                    default:
                        return {};
                }
            };
            
            // 检测各种类型的按钮
            const buttonElements = [
                ...Array.from(document.querySelectorAll('button')).map((el, i) => getButtonInfo(el, 'button_tag', i)),
                ...Array.from(document.querySelectorAll('input[type="button"], input[type="submit"], input[type="reset"]')).map((el, i) => getButtonInfo(el, 'input_button', i)),
                ...Array.from(document.querySelectorAll('[role="button"]')).map((el, i) => getButtonInfo(el, 'role_button', i)),
                ...Array.from(document.querySelectorAll('[onclick]')).map((el, i) => getButtonInfo(el, 'onclick_element', i)),
                ...Array.from(document.querySelectorAll('a[href]')).map((el, i) => getButtonInfo(el, 'clickable_link', i))
            ];
            
            return {
                page_info: {
                    title: document.title,
                    url: location.href,
                    timestamp: new Date().toISOString()
                },
                buttons: buttonElements,
                statistics: {
                    total_buttons: buttonElements.length,
                    visible_buttons: buttonElements.filter(b => b.visible).length,
                    clickable_buttons: buttonElements.filter(b => b.clickable).length
                }
            };
        }
    """)
    
    # 转换为数据类
    buttons = [
        ElementInfo(
            index=btn["index"],
            tag_name=btn["tagName"],
            text=btn["text"],
            id=btn["id"],
            class_name=btn["className"],
            visible=btn["visible"],
            clickable=btn["clickable"],
            position=btn["position"],
            attributes=btn["attributes"],
            styles=btn["styles"]
        )
        for btn in result["buttons"]
    ]
    
    return ButtonDetectionResult(
        page_info=result["page_info"],
        buttons=buttons,
        statistics=result["statistics"]
    )


async def detect_elements_by_selector(page: Page, selector: str, selector_type: str = "css") -> List[ElementInfo]:
    """
    根据选择器检测页面元素
    """
    if selector_type == "css":
        elements = await page.query_selector_all(selector)
    else:  # xpath
        elements = await page.query_selector_all(f"xpath={selector}")
    
    element_infos = []
    for i, element in enumerate(elements):
        try:
            # 获取元素信息
            info = await element.evaluate("""
                (el) => {
                    const rect = el.getBoundingClientRect();
                    const style = getComputedStyle(el);
                    
                    return {
                        tagName: el.tagName.toLowerCase(),
                        text: (el.textContent || "").trim(),
                        id: el.id || null,
                        className: el.className || null,
                        visible: rect.width > 0 && rect.height > 0 && 
                                style.visibility !== 'hidden' && 
                                style.display !== 'none',
                        clickable: !el.disabled,
                        position: {
                            x: Math.round(rect.x),
                            y: Math.round(rect.y),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height)
                        },
                        attributes: Array.from(el.attributes).reduce((acc, attr) => {
                            acc[attr.name] = attr.value;
                            return acc;
                        }, {}),
                        styles: {
                            backgroundColor: style.backgroundColor,
                            color: style.color,
                            fontSize: style.fontSize,
                            display: style.display,
                            cursor: style.cursor
                        }
                    };
                }
            """)
            
            element_infos.append(ElementInfo(
                index=i,
                tag_name=info["tagName"],
                text=info["text"],
                id=info["id"],
                class_name=info["className"],
                visible=info["visible"],
                clickable=info["clickable"],
                position=info["position"],
                attributes=info["attributes"],
                styles=info["styles"]
            ))
        except Exception as e:
            print(f"⚠️ 获取元素信息失败: {e}")
            continue
    
    return element_infos


async def hover_and_detect_dynamic_elements(
    page: Page, 
    hover_selector: str, 
    target_selector: str,
    wait_time: int = 1500
) -> List[ElementInfo]:
    """
    悬停后检测动态出现的元素
    借鉴自 screenshot_menu_bar.py 的悬停交互功能
    """
    try:
        # 获取悬停元素
        hover_element = await page.query_selector(hover_selector)
        if not hover_element:
            print(f"❌ 未找到悬停元素: {hover_selector}")
            return []
        
        # 获取元素位置
        box = await hover_element.bounding_box()
        if not box:
            print(f"❌ 无法获取悬停元素位置")
            return []
        
        # 悬停操作
        x, y = box["x"] + box["width"] // 2, box["y"] + box["height"] // 2
        await page.mouse.move(x, y)
        await page.wait_for_timeout(wait_time)
        
        # 检测动态出现的元素
        dynamic_elements = await detect_elements_by_selector(page, target_selector)
        
        print(f"✅ 悬停后检测到 {len(dynamic_elements)} 个动态元素")
        return dynamic_elements
        
    except Exception as e:
        print(f"❌ 悬停检测失败: {e}")
        return []


async def take_screenshot_with_elements(
    page: Page, 
    elements: List[ElementInfo], 
    screenshot_path: str,
    highlight_elements: bool = True
) -> str:
    """
    截图并高亮显示指定元素
    """
    if highlight_elements:
        # 添加高亮样式
        await page.add_style_tag(content="""
            .highlight-element {
                outline: 2px solid red !important;
                outline-offset: 2px !important;
                background-color: rgba(255, 0, 0, 0.1) !important;
            }
        """)
        
        # 为元素添加高亮类
        for element in elements:
            try:
                await page.evaluate(f"""
                    (index) => {{
                        const elements = document.querySelectorAll('*');
                        if (elements[index]) {{
                            elements[index].classList.add('highlight-element');
                        }}
                    }}
                """, element.index)
            except Exception:
                continue
    
    # 截图
    await page.screenshot(path=screenshot_path, full_page=True)
    print(f"📸 截图已保存到: {screenshot_path}")
    
    return screenshot_path
