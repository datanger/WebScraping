#!/usr/bin/env python3
"""
Windows兼容性测试脚本
用于测试项目在Windows环境下的兼容性
"""

import os
import sys
import platform
from pathlib import Path

def test_platform_detection():
    """测试平台检测功能"""
    print("🔍 平台检测测试")
    print(f"   操作系统: {platform.system()}")
    print(f"   系统版本: {platform.version()}")
    print(f"   架构: {platform.machine()}")
    print(f"   Python版本: {sys.version}")
    print()

def test_path_handling():
    """测试路径处理功能"""
    print("📁 路径处理测试")
    
    # 测试项目根目录获取
    project_root = Path(__file__).parent.parent
    print(f"   项目根目录: {project_root}")
    
    # 测试下载目录
    downloads_dir = project_root / "downloads"
    print(f"   下载目录: {downloads_dir}")
    print(f"   下载目录存在: {downloads_dir.exists()}")
    
    # 测试用户目录
    home_dir = Path.home()
    print(f"   用户目录: {home_dir}")
    
    # 测试系统特定的下载目录
    system = platform.system()
    if system == "Windows":
        default_downloads = home_dir / "Downloads"
        chinese_downloads = home_dir / "下载"
        print(f"   Windows默认下载目录: {default_downloads}")
        print(f"   Windows中文下载目录: {chinese_downloads}")
    else:
        default_downloads = home_dir / "Downloads"
        chinese_downloads = home_dir / "下载"
        print(f"   Linux/macOS默认下载目录: {default_downloads}")
        print(f"   Linux/macOS中文下载目录: {chinese_downloads}")
    
    print()

def test_browser_detection():
    """测试浏览器检测功能"""
    print("🌐 浏览器检测测试")
    
    # 导入浏览器检测函数
    sys.path.append(str(Path(__file__).parent))
    try:
        from scan_with_existing_browser_cdp import find_browser_executable
        browser_path = find_browser_executable()
        if browser_path:
            print(f"   ✅ 找到浏览器: {browser_path}")
        else:
            print("   ❌ 未找到浏览器")
    except Exception as e:
        print(f"   ❌ 浏览器检测失败: {e}")
    
    print()

def test_user_data_directory():
    """测试用户数据目录创建"""
    print("📂 用户数据目录测试")
    
    system = platform.system()
    if system == "Windows":
        user_data_dir = Path.home() / "AppData" / "Local" / "debug_browser"
    else:  # Linux/macOS
        user_data_dir = Path.home() / ".config" / "debug_browser"
    
    print(f"   用户数据目录: {user_data_dir}")
    
    try:
        user_data_dir.mkdir(parents=True, exist_ok=True)
        print(f"   ✅ 目录创建成功: {user_data_dir.exists()}")
    except Exception as e:
        print(f"   ❌ 目录创建失败: {e}")
    
    print()

def test_download_paths():
    """测试下载路径检测"""
    print("📥 下载路径检测测试")
    
    system = platform.system()
    test_file = "test_file.zip"
    
    if system == "Windows":
        possible_paths = [
            Path.home() / "Downloads" / test_file,
            Path.home() / "下载" / test_file,  # 中文系统
            Path("downloads") / test_file,
            Path.cwd() / "downloads" / test_file
        ]
    else:  # Linux/macOS
        possible_paths = [
            Path.home() / "Downloads" / test_file,
            Path.home() / "下载" / test_file,  # 中文系统
            Path("downloads") / test_file,
            Path.cwd() / "downloads" / test_file
        ]
    
    print("   可能的下载路径:")
    for i, path in enumerate(possible_paths, 1):
        print(f"   {i}. {path} (存在: {path.parent.exists()})")
    
    print()

def test_imports():
    """测试关键模块导入"""
    print("📦 模块导入测试")
    
    modules_to_test = [
        "pathlib",
        "platform",
        "os",
        "sys",
        "json",
        "asyncio",
        "datetime",
        "shutil"
    ]
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"   ✅ {module_name}")
        except ImportError as e:
            print(f"   ❌ {module_name}: {e}")
    
    # 测试第三方模块
    third_party_modules = [
        "playwright",
        "dotenv",
        "tenacity",
        "pyotp",
        "aiofiles",
        "watchdog"
    ]
    
    print("   第三方模块:")
    for module_name in third_party_modules:
        try:
            __import__(module_name)
            print(f"   ✅ {module_name}")
        except ImportError as e:
            print(f"   ❌ {module_name}: {e}")
    
    print()

def test_file_operations():
    """测试文件操作"""
    print("📄 文件操作测试")
    
    # 测试临时文件创建
    test_file = Path("test_windows_compatibility.tmp")
    try:
        test_file.write_text("Windows兼容性测试")
        print(f"   ✅ 文件创建成功: {test_file}")
        
        # 测试文件读取
        content = test_file.read_text()
        print(f"   ✅ 文件读取成功: {len(content)} 字符")
        
        # 测试文件删除
        test_file.unlink()
        print(f"   ✅ 文件删除成功: {not test_file.exists()}")
        
    except Exception as e:
        print(f"   ❌ 文件操作失败: {e}")
        # 清理测试文件
        if test_file.exists():
            try:
                test_file.unlink()
            except:
                pass
    
    print()

def main():
    """主测试函数"""
    print("🧪 Windows兼容性测试")
    print("=" * 50)
    print()
    
    test_platform_detection()
    test_path_handling()
    test_browser_detection()
    test_user_data_directory()
    test_download_paths()
    test_imports()
    test_file_operations()
    
    print("✅ 兼容性测试完成")
    print()
    print("📋 测试总结:")
    print("   - 如果所有测试都通过，说明项目已适配Windows")
    print("   - 如果有失败的测试，请检查相应的配置或依赖")
    print("   - 建议在Windows环境中运行此测试脚本")

if __name__ == "__main__":
    main()
