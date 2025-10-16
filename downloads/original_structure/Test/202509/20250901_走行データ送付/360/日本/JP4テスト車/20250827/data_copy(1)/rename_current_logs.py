#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动重命名当前日志文件夹
将 20250915_113652 重命名为 RV1_20250826
"""

import os
import shutil

def rename_current_logs():
    """重命名当前日志文件夹"""
    print("🔄 手动重命名日志文件夹...")
    
    # 源目录（包含完整内容的日志）
    source_dir = "data_copy_modules/logs/20250915_113652"
    
    # 目标目录（使用车号和Vector日期）
    target_dir = "data_copy_modules/logs/RV1_20250826"
    
    # 检查源目录是否存在
    if not os.path.exists(source_dir):
        print(f"❌ 源目录不存在: {source_dir}")
        return False
    
    # 检查目标目录是否已存在
    if os.path.exists(target_dir):
        print(f"⚠️ 目标目录已存在: {target_dir}")
        choice = input("是否删除现有目录并继续？(y/n): ").lower().strip()
        if choice != 'y':
            print("❌ 操作取消")
            return False
        shutil.rmtree(target_dir)
        print(f"✅ 已删除现有目录: {target_dir}")
    
    try:
        # 移动目录
        shutil.move(source_dir, target_dir)
        print(f"✅ 日志目录重命名成功:")
        print(f"   源目录: {source_dir}")
        print(f"   目标目录: {target_dir}")
        
        # 检查文件内容
        datacopy_file = os.path.join(target_dir, "datacopy.txt")
        filelist_file = os.path.join(target_dir, "filelist.txt")
        
        if os.path.exists(datacopy_file):
            with open(datacopy_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            print(f"📄 datacopy.txt: {len(lines)} 行")
        
        if os.path.exists(filelist_file):
            with open(filelist_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            print(f"📄 filelist.txt: {len(lines)} 行")
        
        # 删除多余的目录（如果存在）
        extra_dir = "data_copy_modules/logs/3NRV1_20250826_113652"
        if os.path.exists(extra_dir):
            shutil.rmtree(extra_dir)
            print(f"✅ 已删除多余目录: {extra_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ 重命名失败: {e}")
        return False

def main():
    """主函数"""
    print("="*60)
    print("日志文件夹重命名工具")
    print("="*60)
    print("将 20250915_113652 重命名为 RV1_20250826")
    print("保留完整的拷贝日志内容")
    print("="*60)
    
    success = rename_current_logs()
    
    if success:
        print("\n✅ 重命名完成！")
        print("现在日志文件夹名称: RV1_20250826")
        print("包含完整的拷贝日志内容")
    else:
        print("\n❌ 重命名失败！")

if __name__ == "__main__":
    main()
