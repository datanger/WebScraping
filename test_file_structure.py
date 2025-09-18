#!/usr/bin/env python3
"""
简单的文件结构获取测试脚本
"""

import asyncio
import sys
sys.path.append('.')

from playwright.async_api import async_playwright

async def test_file_structure():
    """测试文件结构获取"""
    print("🧪 测试文件结构获取")
    print("=" * 50)
    
    playwright = await async_playwright().start()
    
    try:
        # 连接到现有浏览器
        browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
        contexts = browser.contexts
        
        if not contexts:
            print("❌ 未找到浏览器上下文")
            return
            
        context = contexts[0]
        pages = context.pages
        
        if not pages:
            print("❌ 未找到页面")
            return
            
        # 找到SharePoint页面
        sharepoint_page = None
        for page in pages:
            title = await page.title()
            url = page.url
            if 'sharepoint.com' in url or 'KOTEI' in title:
                sharepoint_page = page
                break
                
        if not sharepoint_page:
            sharepoint_page = pages[0]
            
        print(f"✅ 使用页面: {await sharepoint_page.title()}")
        print(f"   页面URL: {sharepoint_page.url}")
        
        # 简单的文件结构获取测试
        print("\n🔍 开始获取文件结构...")
        
        elements = await sharepoint_page.evaluate("""
            () => {
                const elements = [];
                const seen = new Set();
                
                // 尝试多个选择器
                const selectors = [
                    '.heroTextWithHeroCommandsWrapped2_c5aceefe',
                    '.field-LinkFilename-htmlGrid_1',
                    '[role="row"]:not(.headerRow_e4dc14da)',
                    '.row_e4dc14da',
                    'a[href*="id="]',
                    'a[href*="FolderCTID"]'
                ];
                
                selectors.forEach(selector => {
                    try {
                        const elements_found = document.querySelectorAll(selector);
                        console.log(`选择器 ${selector} 找到 ${elements_found.length} 个元素`);
                        
                        elements_found.forEach(el => {
                            const text = el.textContent?.trim();
                            if (text && text.length > 0 && text.length < 100) {
                                // 排除表头
                                const headerTexts = ['名称', '修改时间', '修改者', '文件大小', '子文件夹计数', '子项目计数', '创建时间', '创建者'];
                                if (headerTexts.includes(text)) {
                                    return;
                                }
                                
                                if (!seen.has(text)) {
                                    seen.add(text);
                                    elements.push({
                                        text: text,
                                        selector: selector,
                                        tagName: el.tagName,
                                        className: el.className
                                    });
                                }
                            }
                        });
                    } catch (e) {
                        console.log(`选择器 ${selector} 出错:`, e);
                    }
                });
                
                return elements;
            }
        """)
        
        print(f"✅ 找到 {len(elements)} 个元素:")
        for i, element in enumerate(elements[:10]):  # 只显示前10个
            print(f"   {i+1}. {element['text']} (选择器: {element['selector']})")
            
        if len(elements) > 10:
            print(f"   ... 还有 {len(elements) - 10} 个元素")
            
        return len(elements) > 0
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await playwright.stop()

if __name__ == "__main__":
    success = asyncio.run(test_file_structure())
    if success:
        print("\n✅ 文件结构获取测试成功")
    else:
        print("\n❌ 文件结构获取测试失败")
