#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交互式数据拷贝工具启动脚本
Interactive Data Copy Tool Launcher
"""

import sys
import os

# 添加模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'data_copy_modules'))

try:
    from interactive_main import main
    print("正在启动交互式数据拷贝工具...")
    main()
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("请确保在正确的目录下运行此脚本")
    print("当前目录:", os.getcwd())
except Exception as e:
    print(f"❌ 启动失败: {e}")
    import traceback
    traceback.print_exc()
