#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
恢复进度条显示到覆盖模式
"""

import shutil
import os

def restore_progress_display():
    """恢复进度条显示到原来的覆盖模式"""
    try:
        # 恢复备份文件
        shutil.copy2('detailed_progress_backup.py', 'data_copy_modules/utils/detailed_progress.py')
        print("✅ 进度条显示已恢复到覆盖模式")
        print("📝 现在进度条会清屏并覆盖控制台输出")
        return True
    except Exception as e:
        print(f"❌ 恢复失败: {e}")
        return False

if __name__ == "__main__":
    restore_progress_display()
