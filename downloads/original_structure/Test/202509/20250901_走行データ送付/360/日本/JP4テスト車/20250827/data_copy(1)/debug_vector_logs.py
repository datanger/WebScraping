#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试Vector logs文件夹问题
"""

import os
import sys
import datetime

# 添加模块路径
sys.path.append('data_copy_modules')

def debug_vector_logs():
    """调试Vector logs文件夹问题"""
    print("🔍 调试Vector logs文件夹问题...")
    print("="*60)
    
    # 检查当前目录下的所有驱动器
    print("📋 检查当前目录下的所有驱动器:")
    for drive in ['C:', 'D:', 'E:', 'F:', 'G:', 'H:', 'I:', 'J:', 'K:', 'L:', 'M:', 'N:', 'O:', 'P:', 'Q:', 'R:', 'S:', 'T:', 'U:', 'V:', 'W:', 'X:', 'Y:', 'Z:']:
        if os.path.exists(drive):
            print(f"   {drive} - 存在")
            
            # 检查是否有logs文件夹
            logs_path = os.path.join(drive, 'logs')
            if os.path.exists(logs_path):
                print(f"      📁 logs文件夹存在: {logs_path}")
                
                # 检查logs文件夹中的文件
                try:
                    files = os.listdir(logs_path)
                    if files:
                        print(f"         📄 包含 {len(files)} 个文件/文件夹")
                        
                        # 检查文件的创建日期
                        earliest_date = None
                        for file in files[:5]:  # 只检查前5个文件
                            file_path = os.path.join(logs_path, file)
                            print(f"            检查文件: {file}")
                            print(f"            完整路径: {file_path}")
                            print(f"            是否为文件: {os.path.isfile(file_path)}")
                            
                            if os.path.isfile(file_path):
                                try:
                                    creation_time = os.path.getctime(file_path)
                                    print(f"            创建时间戳: {creation_time}")
                                    file_date = datetime.datetime.fromtimestamp(creation_time).strftime("%Y%m%d")
                                    print(f"            格式化日期: {file_date}")
                                    if earliest_date is None or file_date < earliest_date:
                                        earliest_date = file_date
                                except Exception as e:
                                    print(f"            {file}: 无法获取日期 - {e}")
                                    import traceback
                                    traceback.print_exc()
                            else:
                                print(f"            {file}: 不是文件，跳过")
                        
                        if earliest_date:
                            print(f"         📅 最早日期: {earliest_date}")
                        else:
                            print(f"         ⚠️ 无法确定最早日期")
                    else:
                        print(f"         📄 logs文件夹为空")
                except Exception as e:
                    print(f"         ❌ 无法访问logs文件夹: {e}")
            else:
                print(f"      📁 logs文件夹不存在")
        else:
            print(f"   {drive} - 不存在")
    
    print()
    print("🔍 检查完成！")

def main():
    """主函数"""
    print("Vector logs调试工具")
    print("检查所有驱动器中的logs文件夹")
    debug_vector_logs()

if __name__ == "__main__":
    main()
