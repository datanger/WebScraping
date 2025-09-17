#!/usr/bin/env python3
"""
连接到现有浏览器实例
用途：查找并连接到已经运行的浏览器进程
使用场景：当浏览器已经在调试模式下运行时，此脚本可以找到并连接到它
"""

import asyncio
import sys
import subprocess
import os
from pathlib import Path

sys.path.append('.')
from playwright.async_api import async_playwright


async def find_existing_browser():
    """查找现有的浏览器进程并尝试连接"""
    print("🔍 查找现有浏览器进程...")
    
    # 查找 Edge 浏览器进程
    try:
        result = subprocess.run(['pgrep', '-f', 'microsoft-edge'], capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"   找到 {len(pids)} 个 Edge 浏览器进程")
            
            # 尝试连接到每个进程
            for pid in pids:
                if pid.strip():
                    print(f"   尝试连接进程 {pid}...")
                    # 这里我们需要找到该进程使用的调试端口
                    # 通常需要检查进程的启动参数
                    
    except Exception as e:
        print(f"   查找进程失败: {e}")


async def connect_to_existing_browser():
    """连接到现有浏览器"""
    print("🔗 尝试连接到现有浏览器...")
    
    async with async_playwright() as p:
        # 尝试常见的调试端口
        ports = [9222, 9223, 9224, 9225, 9226, 9227, 9228, 9229, 9230]
        
        for port in ports:
            try:
                print(f"   尝试端口 {port}...")
                browser = await p.chromium.connect_over_cdp(f"http://localhost:{port}")
                
                contexts = browser.contexts
                print(f"   ✅ 端口 {port} 连接成功！")
                print(f"   找到 {len(contexts)} 个浏览器上下文")
                
                if contexts:
                    context = contexts[0]
                    pages = context.pages
                    print(f"   找到 {len(pages)} 个标签页")
                    
                    # 显示当前标签页信息
                    for i, page in enumerate(pages):
                        try:
                            title = await page.title()
                            url = page.url
                            print(f"   标签页 {i+1}: {title}")
                            print(f"      URL: {url}")
                        except:
                            print(f"   标签页 {i+1}: 无法获取信息")
                
                await browser.close()
                return port
                
            except Exception as e:
                print(f"   ❌ 端口 {port} 连接失败")
        
        print("   ❌ 所有端口都无法连接")
        return None


async def start_browser_with_existing_profile():
    """使用现有用户配置文件启动浏览器"""
    print("🚀 使用现有配置文件启动浏览器...")
    
    # 查找现有的用户数据目录
    possible_dirs = [
        Path.home() / ".config" / "microsoft-edge",
        Path.home() / ".config" / "google-chrome",
        Path.home() / ".mozilla" / "firefox",
    ]
    
    user_data_dir = None
    for dir_path in possible_dirs:
        if dir_path.exists():
            user_data_dir = str(dir_path)
            print(f"   找到用户数据目录: {user_data_dir}")
            break
    
    if not user_data_dir:
        print("   ❌ 未找到现有用户数据目录")
        return False
    
    # 启动浏览器
    cmd = [
        "microsoft-edge",
        "--remote-debugging-port=9222",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check"
    ]
    
    try:
        print(f"   启动命令: {' '.join(cmd)}")
        process = subprocess.Popen(cmd)
        print(f"   ✅ 浏览器已启动 (PID: {process.pid})")
        return True
    except Exception as e:
        print(f"   ❌ 启动失败: {e}")
        return False


async def main():
    """主函数"""
    print("🚀 连接到现有浏览器")
    print("=" * 50)
    
    # 方法1：尝试连接现有浏览器
    port = await connect_to_existing_browser()
    
    if port:
        print(f"\n✅ 成功连接到现有浏览器 (端口 {port})")
        print("   现在可以运行扫描脚本了")
        return
    
    # 方法2：使用现有配置文件启动
    print("\n" + "=" * 50)
    if await start_browser_with_existing_profile():
        print("\n✅ 使用现有配置文件启动成功")
        print("   请在浏览器中完成登录，然后运行扫描脚本")
    else:
        print("\n❌ 无法连接到现有浏览器")
        print("💡 建议：")
        print("   1. 确保浏览器正在运行")
        print("   2. 手动启动浏览器并开启调试模式")
        print("   3. 或者使用独立的调试浏览器")


if __name__ == "__main__":
    asyncio.run(main())
