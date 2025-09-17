#!/usr/bin/env python3
"""
浏览器进程管理工具
用于查看、关闭调试模式浏览器进程
"""

import subprocess
import sys
import os


def list_browser_processes():
    """列出所有调试模式的浏览器进程"""
    print("🔍 查找调试模式浏览器进程...")
    
    try:
        # 查找包含 remote-debugging-port 的进程
        result = subprocess.run(
            ["ps", "aux"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        lines = result.stdout.split('\n')
        debug_processes = []
        
        for line in lines:
            if 'remote-debugging-port=9222' in line:
                debug_processes.append(line)
        
        if debug_processes:
            print("✅ 找到调试模式浏览器进程:")
            for i, process in enumerate(debug_processes, 1):
                print(f"   {i}. {process}")
        else:
            print("❌ 未找到调试模式浏览器进程")
            print("💡 请先运行: python scripts/start_debug_browser.py")
        
        return debug_processes
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 执行命令失败: {e}")
        return []


def kill_browser_processes():
    """关闭所有调试模式浏览器进程"""
    print("🛑 关闭调试模式浏览器进程...")
    
    try:
        # 使用 pkill 关闭包含 remote-debugging-port=9222 的进程
        result = subprocess.run(
            ["pkill", "-f", "remote-debugging-port=9222"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ 浏览器进程已关闭")
        else:
            print("❌ 未找到可关闭的浏览器进程")
            
    except Exception as e:
        print(f"❌ 关闭进程失败: {e}")


def check_browser_status():
    """检查浏览器调试端口是否可用"""
    print("🔍 检查浏览器调试端口状态...")
    
    try:
        import requests
        response = requests.get("http://localhost:9222/json", timeout=2)
        if response.status_code == 200:
            print("✅ 浏览器调试端口 (9222) 可用")
            tabs = response.json()
            print(f"   当前打开的标签页数量: {len(tabs)}")
            return True
        else:
            print("❌ 浏览器调试端口不可用")
            return False
    except ImportError:
        print("💡 需要安装 requests 库来检查端口状态")
        return False
    except Exception as e:
        print(f"❌ 检查端口状态失败: {e}")
        return False


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("🚀 浏览器进程管理工具")
        print("=" * 40)
        print("用法:")
        print("  python browser_manager.py list    - 列出浏览器进程")
        print("  python browser_manager.py kill    - 关闭浏览器进程")
        print("  python browser_manager.py status  - 检查端口状态")
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        list_browser_processes()
    elif command == "kill":
        kill_browser_processes()
    elif command == "status":
        check_browser_status()
    else:
        print(f"❌ 未知命令: {command}")
        print("可用命令: list, kill, status")


if __name__ == "__main__":
    main()
