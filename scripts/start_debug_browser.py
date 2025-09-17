#!/usr/bin/env python3
"""
启动带调试模式的浏览器
用途：启动浏览器并开启调试端口，供其他脚本连接使用
使用场景：当需要手动登录SharePoint后，让其他脚本连接到此浏览器进行自动化操作
"""

import subprocess
import sys
import time
import os
from pathlib import Path


def find_browser_executable():
    """查找浏览器可执行文件"""
    possible_paths = [
        # Edge
        "/usr/bin/microsoft-edge",
        "/usr/bin/msedge",
        "/snap/bin/microsoft-edge",
        "/opt/microsoft/msedge/msedge",
        # Chrome
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
        "/opt/google/chrome/chrome",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


def start_debug_browser():
    """启动带调试模式的浏览器"""
    print("🔍 查找浏览器可执行文件...")
    
    browser_path = find_browser_executable()
    if not browser_path:
        print("❌ 未找到浏览器可执行文件")
        print("💡 请手动安装 Edge 或 Chrome 浏览器")
        return False
    
    print(f"✅ 找到浏览器: {browser_path}")
    
    # 创建用户数据目录
    user_data_dir = Path.home() / ".config" / "debug_browser"
    user_data_dir.mkdir(parents=True, exist_ok=True)
    
    # 启动命令
    cmd = [
        browser_path,
        "--remote-debugging-port=9222",
        "--user-data-dir=" + str(user_data_dir),
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-web-security",
        "--disable-features=VizDisplayCompositor"
    ]
    
    print("🚀 启动带调试模式的浏览器...")
    print(f"   命令: {' '.join(cmd)}")
    print("   调试端口: 9222")
    print("   用户数据目录:", user_data_dir)
    print()
    print("📋 使用说明:")
    print("   1. 浏览器启动后，请手动登录到 SharePoint")
    print("   2. 登录完成后，运行扫描脚本")
    print("   3. 脚本将连接到这个浏览器实例")
    print()
    
    try:
        # 启动浏览器（分离进程，程序退出后浏览器继续运行）
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )
        print(f"✅ 浏览器已启动 (PID: {process.pid})")
        print("   浏览器将在后台持续运行，即使程序退出也不会关闭")
        print("   请在浏览器中完成登录，然后按回车键继续...")
        input()
        
        # 不等待进程结束，让浏览器在后台继续运行
        print("💡 浏览器进程已分离，程序退出后浏览器将继续运行")
        print("   如需关闭浏览器，请手动关闭或使用任务管理器")
        
        return True
        
    except Exception as e:
        print(f"❌ 启动浏览器失败: {e}")
        return False


def main():
    """主函数"""
    print("🚀 启动调试模式浏览器")
    print("=" * 50)
    
    if start_debug_browser():
        print("✅ 浏览器启动成功")
        print("💡 现在可以运行扫描脚本了:")
        print("   python scripts/scan_with_existing_browser.py")
        print()
        print("🔧 浏览器管理命令:")
        print("   查看运行中的浏览器进程: ps aux | grep -E '(chrome|msedge|chromium)'")
        print("   关闭浏览器进程: pkill -f 'remote-debugging-port=9222'")
    else:
        print("❌ 浏览器启动失败")


if __name__ == "__main__":
    main()
