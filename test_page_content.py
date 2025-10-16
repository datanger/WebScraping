#!/usr/bin/env python3
"""
测试页面内容，查看所有可见的文本元素
"""
import asyncio
from playwright.async_api import async_playwright

async def test_page_content():
    """测试页面内容"""
    async with async_playwright() as pw:
        try:
            # 连接到现有浏览器
            browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
            contexts = browser.contexts
            context = contexts[0] if contexts else await browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()
            
            print(f"当前页面URL: {page.url}")
            print(f"页面标题: {await page.title()}")
            
            # 多次滚动页面
            for i in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)
                print(f"滚动 {i+1}/3 完成")
            
            # 获取所有可见文本
            all_texts = await page.evaluate("""
                () => {
                    const texts = [];
                    const elements = document.querySelectorAll('*');
                    
                    elements.forEach(el => {
                        const text = el.textContent?.trim();
                        if (text && text.length > 0 && text.length < 100) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                texts.push({
                                    text: text,
                                    tag: el.tagName,
                                    className: el.className,
                                    id: el.id
                                });
                            }
                        }
                    });
                    
                    return texts;
                }
            """)
            
            print(f"\n找到 {len(all_texts)} 个文本元素:")
            for i, item in enumerate(all_texts[:20]):  # 只显示前20个
                print(f"{i+1:2d}. '{item['text']}' (tag: {item['tag']}, class: {item['className'][:50]})")
            
            # 查找包含zip的文本
            zip_texts = [item for item in all_texts if 'zip' in item['text'].lower()]
            print(f"\n包含'zip'的文本 ({len(zip_texts)} 个):")
            for item in zip_texts:
                print(f"  - '{item['text']}' (tag: {item['tag']})")
                
        except Exception as e:
            print(f"错误: {e}")

if __name__ == "__main__":
    asyncio.run(test_page_content())
