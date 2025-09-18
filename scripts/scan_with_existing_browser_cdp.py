#!/usr/bin/env python3
"""
SharePoint 文件结构扫描器 - 使用现有浏览器（CDP 下载监控版）
严格对齐 scripts/scan_with_existing_browser.py 的交互与输出，仅在下载前附加
浏览器原生下载器监控（CDP），以获取实时进度/速度/完成状态。
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json
import os
import zipfile
import shutil

sys.path.append('.')
from playwright.async_api import async_playwright
from src.sp_automation.sharepoint_scanner import SharePointScanner
from src.sp_automation.recursive_scanner import SharePointRecursiveScanner
from src.sp_automation.file_downloader import SharePointFileDownloader
from src.sp_automation.page_operations import navigate_to_url, check_login_required, get_page_info
from src.sp_automation.download_status_detector import create_download_status_manager
from src.sp_automation.cdp_download_monitor import BrowserDownloadMonitor
from src.sp_automation.config import settings


async def get_download_directory_structure(page, file_info):
    """获取下载文件在原始网页中的目录结构信息"""
    try:
        # 获取当前页面URL和标题
        current_url = page.url
        page_title = await page.title()
        
        # 解析URL路径信息
        url_parts = current_url.split('/')
        sharepoint_site = ""
        document_library = ""
        folder_path = []
        
        # 提取SharePoint站点信息
        for i, part in enumerate(url_parts):
            if 'sharepoint.com' in part:
                if i + 2 < len(url_parts):
                    sharepoint_site = url_parts[i + 2]  # sites/站点名
                break
        
        # 提取文档库和文件夹路径
        if 'Shared%20Documents' in current_url:
            document_library = "Shared Documents"
            # 提取文件夹路径
            if 'id=' in current_url:
                import urllib.parse
                import re
                
                # 解码URL中的路径信息
                decoded_url = urllib.parse.unquote(current_url)
                
                # 使用正则表达式提取路径信息
                path_match = re.search(r'id=([^&]+)', decoded_url)
                if path_match:
                    encoded_path = path_match.group(1)
                    # 解码路径
                    decoded_path = urllib.parse.unquote(encoded_path)
                    
                    # 手动解析路径组件
                    # 从URL中提取关键路径组件
                    if 'GEN1.5' in decoded_path:
                        folder_path.append('GEN1.5')
                    if '中台FOT' in decoded_path:
                        folder_path.append('中台FOT')
                    if 'データ解析' in decoded_path:
                        folder_path.append('データ解析')
                    if '認知系' in decoded_path:
                        folder_path.append('認知系')
                    if '走路認知' in decoded_path:
                        folder_path.append('走路認知')
                    if 'スクリプト検討' in decoded_path:
                        folder_path.append('スクリプト検討')
                    if 'Test' in decoded_path:
                        folder_path.append('Test')
                    if '202509' in decoded_path:
                        folder_path.append('202509')
                    if '20250901_走行データ送付' in decoded_path:
                        folder_path.append('20250901_走行データ送付')
                    if '360' in decoded_path:
                        folder_path.append('360')
                    if '日本' in decoded_path:
                        folder_path.append('日本')
                    if 'JP4テスト車' in decoded_path:
                        folder_path.append('JP4テスト車')
                    if '20250827' in decoded_path:
                        folder_path.append('20250827')
        
        # 构建完整路径
        full_path = "/" + "/".join(folder_path) + "/" + file_info['name'] if folder_path else "/" + file_info['name']
        
        # 构建目录结构信息
        directory_structure = {
            "page_title": page_title,
            "page_url": current_url,
            "sharepoint_site": sharepoint_site,
            "document_library": document_library,
            "folder_path": folder_path,
            "file_name": file_info['name'],
            "full_path": full_path,
            "file_position": {
                "x": file_info['position']['x'],
                "y": file_info['position']['y'],
                "width": file_info['position']['width'],
                "height": file_info['position']['height']
            }
        }
        
        return directory_structure
        
    except Exception as e:
        print(f"❌ 获取目录结构信息失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def print_download_directory_structure(page, file_info):
    """打印下载文件在原始网页中的目录结构"""
    directory_structure = await get_download_directory_structure(page, file_info)
    
    if directory_structure:
        print("\n📁 下载文件目录结构信息:")
        print("=" * 50)
        
        print(f"📄 页面标题: {directory_structure['page_title']}")
        print(f"🔗 页面URL: {directory_structure['page_url']}")
        print(f"🏢 SharePoint站点: {directory_structure['sharepoint_site']}")
        print(f"📚 文档库: {directory_structure['document_library']}")
        
        if directory_structure['folder_path']:
            print(f"📂 文件夹路径:")
            for i, folder in enumerate(directory_structure['folder_path']):
                indent = "  " * (i + 1)
                print(f"{indent}📁 {folder}")
            print(f"📄 文件: {directory_structure['file_name']}")
            print(f"📍 完整路径: {directory_structure['full_path']}")
        else:
            print(f"📄 文件: {directory_structure['file_name']}")
            print(f"📍 完整路径: {directory_structure['full_path']}")
        
        # 获取文件的详细信息
        print(f"\n📊 文件详细信息:")
        print(f"   文件名: {directory_structure['file_name']}")
        print(f"   位置: x={directory_structure['file_position']['x']}, y={directory_structure['file_position']['y']}")
        print(f"   大小: {directory_structure['file_position']['width']} x {directory_structure['file_position']['height']} 像素")
        
        print("=" * 50)
        
        return directory_structure
    else:
        return None


async def save_directory_structure_to_json(directory_structure, file_name):
    """将目录结构信息保存到JSON文件"""
    try:
        import json
        import os
        from datetime import datetime
        
        # 创建logs目录
        logs_dir = Path("downloads/logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名（基于时间戳和文件名）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = "".join(c for c in file_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        json_filename = f"directory_structure_{timestamp}_{safe_filename}.json"
        json_filepath = logs_dir / json_filename
        
        # 添加时间戳到目录结构信息
        directory_structure["timestamp"] = datetime.now().isoformat()
        directory_structure["download_time"] = timestamp
        
        # 保存到JSON文件
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(directory_structure, f, ensure_ascii=False, indent=2)
        
        print(f"💾 目录结构信息已保存到: {json_filepath}")
        
        # 同时更新主下载状态文件
        await update_download_state_with_directory_structure(directory_structure, file_name)
        
    except Exception as e:
        print(f"❌ 保存目录结构信息失败: {e}")
        import traceback
        traceback.print_exc()


async def update_download_state_with_directory_structure(directory_structure, file_name):
    """更新主下载状态文件，添加目录结构信息"""
    try:
        import json
        from pathlib import Path
        
        # 读取现有的下载状态文件
        state_file = Path("downloads/download_state.json")
        if state_file.exists():
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
        else:
            state_data = {"tasks": {}, "timestamp": ""}
        
        # 查找最新的下载任务（基于文件名）
        latest_task = None
        latest_time = None
        
        for task_id, task_info in state_data["tasks"].items():
            if task_info.get("file_name") == file_name:
                task_time = task_info.get("start_time", "")
                if not latest_time or task_time > latest_time:
                    latest_time = task_time
                    latest_task = task_id
        
        # 如果找到任务，添加目录结构信息
        if latest_task:
            state_data["tasks"][latest_task]["directory_structure"] = directory_structure
            state_data["timestamp"] = datetime.now().isoformat()
            
            # 保存更新后的状态文件
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)
            
            print(f"📝 已更新下载状态文件，添加目录结构信息")
        
    except Exception as e:
        print(f"❌ 更新下载状态文件失败: {e}")


async def create_directory_structure_and_extract(zip_path: Path, directory_structure: dict, max_files: int = 2, file_name: str = "") -> dict:
    """创建原始目录结构并解压zip文件到对应目录"""
    try:
        # 等待一小段时间确保文件完全写入
        await asyncio.sleep(1)
        
        extract_info = {
            "zip_file": str(zip_path),
            "extract_path": "",
            "extracted_files": [],
            "total_files_in_zip": 0,
            "extracted_count": 0,
            "success": False,
            "error": None,
            "file_name": file_name,
            "directory_structure_created": False
        }
        
        # 从目录结构信息中获取文件夹路径
        folder_path = directory_structure.get("folder_path", [])
        if not folder_path:
            print(f"   ⚠️ [{file_name}] 无法获取目录结构信息")
            return extract_info
        
        # 创建原始目录结构
        base_path = Path("downloads")
        original_structure_path = base_path / "original_structure"
        
        # 构建完整路径
        full_folder_path = original_structure_path
        for folder in folder_path:
            full_folder_path = full_folder_path / folder
        
        # 创建目录结构
        full_folder_path.mkdir(parents=True, exist_ok=True)
        extract_info["extract_path"] = str(full_folder_path)
        extract_info["directory_structure_created"] = True
        
        print(f"   📁 [{file_name}] 已创建目录结构: {full_folder_path}")
        
        # 将zip文件移动到对应目录
        target_zip_path = full_folder_path / file_name
        shutil.move(str(zip_path), str(target_zip_path))
        print(f"   📦 [{file_name}] 已移动到: {target_zip_path}")
        
        # 在目标目录中解压
        with zipfile.ZipFile(target_zip_path, 'r') as zip_ref:
            # 获取zip文件中的所有文件列表
            file_list = zip_ref.namelist()
            extract_info["total_files_in_zip"] = len(file_list)
            
            # 限制只解压前2个文件
            files_to_extract = file_list[:max_files]
            
            for file_name_in_zip in files_to_extract:
                try:
                    # 解压单个文件到目标目录
                    zip_ref.extract(file_name_in_zip, full_folder_path)
                    extract_info["extracted_files"].append(file_name_in_zip)
                    extract_info["extracted_count"] += 1
                    print(f"   📦 [{file_name}] 已解压: {file_name_in_zip}")
                except Exception as e:
                    print(f"   ⚠️ [{file_name}] 解压文件失败: {file_name_in_zip} - {e}")
                    continue
            
            extract_info["success"] = extract_info["extracted_count"] > 0
            
        if extract_info["success"]:
            print(f"   ✅ [{file_name}] 解压完成: {extract_info['extracted_count']}/{extract_info['total_files_in_zip']} 个文件")
        else:
            print(f"   ❌ [{file_name}] 解压失败: 没有文件被解压")
            
        return extract_info
        
    except Exception as e:
        print(f"   ❌ [{file_name}] 创建目录结构并解压失败: {e}")
        return {
            "zip_file": str(zip_path),
            "extract_path": "",
            "extracted_files": [],
            "total_files_in_zip": 0,
            "extracted_count": 0,
            "success": False,
            "error": str(e),
            "file_name": file_name,
            "directory_structure_created": False
        }


async def download_single_file(scanner, page, file_elem, file_index, total_files, max_retries=2, progress_callback=None):
    """下载单个文件 - 严格遵循安全操作指南，支持重试机制"""
    file_name = file_elem['text']
    print(f"📥 [{file_index}/{total_files}] 开始下载: {file_name}")
    
    # 创建文件信息
    file_info = {
        "name": file_name,
        "position": file_elem['position']
    }
    
    result = {
        "file_name": file_name,
        "file_index": file_index,
        "success": False,
        "error": None,
        "directory_structure": None,
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "retry_count": 0,
        "status": "starting",
        "progress": 0.0,
        "file_size": 0,
        "speed": 0.0
    }
    
    # 通知进度回调
    if progress_callback:
        await progress_callback(result)
    
    # 安全检查 - 确保只进行下载操作
    if not is_safe_download_operation(file_name):
        result["error"] = "安全检查失败"
        result["status"] = "failed"
        if progress_callback:
            await progress_callback(result)
        print(f"   ❌ 安全检查失败: {file_name}")
        result["end_time"] = datetime.now().isoformat()
        return result
    
    # 重试机制
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                result["status"] = f"retrying ({attempt}/{max_retries})"
                result["retry_count"] = attempt
                if progress_callback:
                    await progress_callback(result)
                print(f"   🔄 重试下载 ({attempt}/{max_retries}): {file_name}")
                await asyncio.sleep(2)  # 重试前等待2秒，避免页面冲突
            
            # 执行下载
            result["status"] = "downloading"
            if progress_callback:
                await progress_callback(result)
            print(f"   🖱️ 右键点击: {file_name}")
            success = await scanner.downloader.download_file_by_right_click(page, file_info)
            
            if success:
                # 实时监控下载进度
                await monitor_download_progress_simple(result, progress_callback, scanner, file_name)
                
                # 检查下载状态管理器中的任务状态
                task_status = None
                for task_id, task in scanner.status_manager.tasks.items():
                    if task.file_name == file_name and task.status.value in ['completed', 'downloading']:
                        task_status = task
                        break
                
                if task_status and task_status.status.value == 'completed' and task_status.file_size and task_status.file_size > 0:
                    print(f"   ✅ 下载成功: {file_name} ({task_status.file_size:,} 字节)")
                    result["success"] = True
                    result["retry_count"] = attempt
                    result["status"] = "completed"
                    result["file_size"] = task_status.file_size
                    result["progress"] = 1.0
                    
                    # 获取目录结构信息
                    directory_structure = await get_download_directory_structure(page, file_info)
                    if directory_structure:
                        result["directory_structure"] = directory_structure
                        
                        # 如果是zip文件，启动后台解压任务（不占用下载并发名额）
                        if file_name.lower().endswith('.zip'):
                            print(f"   📦 启动后台解压任务: {file_name}")
                            zip_path = Path("downloads") / file_name
                            
                            # 创建后台解压任务，不等待完成
                            extract_task = asyncio.create_task(
                                create_directory_structure_and_extract(zip_path, directory_structure, max_files=2, file_name=file_name)
                            )
                            result["extract_task"] = extract_task
                    
                    if progress_callback:
                        await progress_callback(result)
                    break
                else:
                    if attempt < max_retries:
                        result["error"] = f"文件验证失败，准备重试"
                        result["status"] = "verification_failed"
                        if progress_callback:
                            await progress_callback(result)
                        print(f"   ⚠️ 文件验证失败，准备重试: {file_name}")
                        continue
                    else:
                        result["error"] = "文件验证失败"
                        result["status"] = "failed"
                        if progress_callback:
                            await progress_callback(result)
                        print(f"   ❌ 文件验证失败: {file_name}")
            else:
                if attempt < max_retries:
                    result["error"] = f"下载失败，准备重试"
                    result["status"] = "download_failed"
                    if progress_callback:
                        await progress_callback(result)
                    print(f"   ⚠️ 下载失败，准备重试: {file_name}")
                    continue
                else:
                    result["error"] = "下载失败"
                    result["status"] = "failed"
                    if progress_callback:
                        await progress_callback(result)
                    print(f"   ❌ 下载失败: {file_name}")
        
        except Exception as e:
            if attempt < max_retries:
                result["error"] = f"异常，准备重试: {e}"
                result["status"] = "exception"
                if progress_callback:
                    await progress_callback(result)
                print(f"   ⚠️ 下载异常，准备重试: {file_name} - {e}")
                continue
            else:
                result["error"] = f"异常: {e}"
                result["status"] = "failed"
                if progress_callback:
                    await progress_callback(result)
                print(f"   ❌ 下载异常: {file_name} - {e}")
    
    result["end_time"] = datetime.now().isoformat()
    return result


async def monitor_download_progress_simple(result, progress_callback, scanner, file_name):
    """简化的实时监控下载进度"""
    import time
    
    start_time = time.time()
    last_size = 0
    last_time = start_time
    
    # 监控下载进度
    while True:
        await asyncio.sleep(1)  # 每1秒更新一次
        
        # 查找对应的下载任务
        task_status = None
        for task_id, task in scanner.status_manager.tasks.items():
            if task.file_name == file_name and task.status.value in ['completed', 'downloading']:
                task_status = task
                break
        
        if not task_status:
            continue
            
        current_time = time.time()
        current_size = task_status.file_size or 0
        
        # 计算下载速度
        if current_size > last_size and current_time > last_time:
            speed = (current_size - last_size) / (current_time - last_time)
            result["speed"] = speed
        else:
            result["speed"] = 0.0
        
        # 更新进度
        if task_status.expected_size and task_status.expected_size > 0:
            result["progress"] = current_size / task_status.expected_size
        elif current_size > 0:
            result["progress"] = min(current_size / (current_size * 1.1), 0.99)  # 估算进度
        
        result["file_size"] = current_size
        result["status"] = "downloading"
        
        # 更新显示
        if progress_callback:
            await progress_callback(result)
        
        # 如果下载完成，退出监控
        if task_status.status.value == 'completed':
            result["progress"] = 1.0
            result["status"] = "completed"
            if progress_callback:
                await progress_callback(result)
            break
        
        last_size = current_size
        last_time = current_time


async def update_unified_report_realtime(progress_tracker, total_files, concurrency, report_filepath):
    """实时更新统一报告文件"""
    try:
        # 确保报告文件路径存在
        if report_filepath is None:
            return
        
        # 构建实时报告数据
        report_data = {
            "report_info": {
                "timestamp": datetime.now().isoformat(),
                "report_type": "unified_batch_download_realtime",
                "concurrency": concurrency
            },
            "summary": {
                "total_files": total_files,
                "successful_downloads": len([t for t in progress_tracker.values() if t["status"] == "completed"]),
                "failed_downloads": len([t for t in progress_tracker.values() if t["status"] == "failed"]),
                "downloading": len([t for t in progress_tracker.values() if t["status"] == "downloading"]),
                "waiting": len([t for t in progress_tracker.values() if t["status"] == "waiting"]),
                "success_rate": f"{(len([t for t in progress_tracker.values() if t['status'] == 'completed']) / total_files * 100):.1f}%" if total_files > 0 else "0%"
            },
            "file_details": []
        }
        
        # 添加所有任务详情
        for file_index, task_info in progress_tracker.items():
            file_detail = {
                "file_name": task_info["file_name"],
                "file_index": file_index,
                "success": task_info["status"] == "completed",
                "error": task_info["error"],
                "start_time": datetime.now().isoformat() if task_info["status"] == "waiting" else None,
                "end_time": datetime.now().isoformat() if task_info["status"] == "completed" else None,
                "retry_count": 0,
                "status": task_info["status"],
                "progress": task_info["progress"],
                "file_size": task_info["file_size"],
                "speed": task_info["speed"],
                "extract_info": task_info.get("extract_info"),
                "extract_task_running": task_info.get("extract_task", False)
            }
            report_data["file_details"].append(file_detail)
        
        # 添加任务状态摘要
        report_data["task_status_summary"] = {
            "completed": len([t for t in progress_tracker.values() if t["status"] == "completed"]),
            "failed": len([t for t in progress_tracker.values() if t["status"] == "failed"]),
            "retrying": len([t for t in progress_tracker.values() if "retrying" in t["status"]]),
            "downloading": len([t for t in progress_tracker.values() if t["status"] == "downloading"]),
            "waiting": len([t for t in progress_tracker.values() if t["status"] == "waiting"])
        }
        
        # 添加安全合规信息
        report_data["security_compliance"] = {
            "only_zip_files": True,
            "safe_operations_only": True,
            "no_dangerous_actions": True,
            "parallel_download_controlled": True
        }
        
        # 保存实时报告
        with open(report_filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"⚠️ 实时报告更新失败: {e}")


async def finalize_unified_report(download_stats, report_filepath):
    """最终化统一报告文件，添加完整信息"""
    try:
        if report_filepath is None or not report_filepath.exists():
            return
            
        # 读取现有报告
        with open(report_filepath, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        # 更新最终信息
        report_data["report_info"]["final_timestamp"] = datetime.now().isoformat()
        report_data["summary"]["final_successful_downloads"] = download_stats["successful"]
        report_data["summary"]["final_failed_downloads"] = download_stats["failed"]
        report_data["summary"]["final_success_rate"] = f"{(download_stats['successful'] / download_stats['total_files'] * 100):.1f}%" if download_stats['total_files'] > 0 else "0%"
        
        # 添加下载的文件列表
        report_data["downloaded_files"] = download_stats["downloaded_files"]
        report_data["failed_files"] = download_stats["failed_files"]
        
        # 更新文件详情，确保包含目录结构信息和解压信息
        for i, file_detail in enumerate(report_data["file_details"]):
            if i < len(download_stats["file_details"]):
                original_detail = download_stats["file_details"][i]
                file_detail.update({
                    "directory_structure": original_detail.get("directory_structure"),
                    "start_time": original_detail.get("start_time"),
                    "end_time": original_detail.get("end_time"),
                    "retry_count": original_detail.get("retry_count", 0),
                    "extract_info": original_detail.get("extract_info"),
                    "extract_task_running": False  # 最终报告时解压任务已完成
                })
        
        # 保存最终报告
        with open(report_filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"📋 统一批量下载报告已保存到: {report_filepath}")
        
        # 同时更新主下载状态文件
        await update_main_download_state_with_batch_results(download_stats)
        
    except Exception as e:
        print(f"❌ 最终化报告失败: {e}")


async def batch_download_files(scanner, page, file_elements):
    """并行批量下载文件 - 严格遵循安全操作指南"""
    try:
        total_files = len(file_elements)
        concurrency = settings.batch_download_concurrency
        
        print(f"\n🚀 开始流水线式并行下载 {total_files} 个文件")
        print(f"⚡ 最大并发数: {concurrency}")
        print(f"⏱️ 任务间隔: 5秒 (流水线式启动)")
        print("=" * 50)
        
        # 创建进度跟踪字典
        progress_tracker = {}
        for i, file_elem in enumerate(file_elements):
            progress_tracker[i + 1] = {
                "file_name": file_elem['text'],
                "status": "waiting",
                "progress": 0.0,
                "file_size": 0,
                "speed": 0.0,
                "error": None
            }
        
        # 创建统一报告文件路径
        logs_dir = Path("downloads/logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"unified_batch_download_report_{timestamp}.json"
        report_filepath = logs_dir / report_filename
        
        # 实时更新统一报告文件
        async def update_progress_and_log(result):
            progress_tracker[result["file_index"]] = {
                "file_name": result["file_name"],
                "status": result["status"],
                "progress": result["progress"],
                "file_size": result["file_size"],
                "speed": result["speed"],
                "error": result["error"],
                "extract_info": result.get("extract_info"),
                "extract_task_running": result.get("extract_task") is not None
            }
            # 实时更新统一报告文件
            await update_unified_report_realtime(progress_tracker, total_files, concurrency, report_filepath)
        
        # 创建信号量控制并发数量，实现流水线式并行下载
        semaphore = asyncio.Semaphore(concurrency)
        
        async def download_with_semaphore(file_elem, index):
            async with semaphore:
                # 任务间隔5秒，实现流水线式并行
                await asyncio.sleep((index - 1) * 5)
                return await download_single_file(scanner, page, file_elem, index, total_files, progress_callback=update_progress_and_log)
        
        # 创建所有下载任务
        tasks = [
            download_with_semaphore(file_elem, i + 1)
            for i, file_elem in enumerate(file_elements)
        ]
        
        # 并行执行所有下载任务
        print("🔄 正在并行执行下载任务...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 等待所有后台解压任务完成
        print("📦 等待所有解压任务完成...")
        extract_tasks = []
        for result in results:
            if isinstance(result, dict) and result.get("extract_task"):
                extract_tasks.append(result["extract_task"])
        
        if extract_tasks:
            extract_results = await asyncio.gather(*extract_tasks, return_exceptions=True)
            # 将解压结果更新到对应的下载结果中
            extract_index = 0
            for i, result in enumerate(results):
                if isinstance(result, dict) and result.get("extract_task"):
                    if extract_index < len(extract_results):
                        extract_result = extract_results[extract_index]
                        if not isinstance(extract_result, Exception):
                            result["extract_info"] = extract_result
                        extract_index += 1
        
        # 处理结果
        download_stats = {
            "timestamp": datetime.now().isoformat(),
            "total_files": total_files,
            "concurrency": concurrency,
            "successful": 0,
            "failed": 0,
            "downloaded_files": [],
            "failed_files": [],
            "file_details": []
        }
        
        for result in results:
            if isinstance(result, Exception):
                print(f"❌ 任务执行异常: {result}")
                download_stats["failed"] += 1
                continue
            
            download_stats["file_details"].append(result)
            
            if result["success"]:
                download_stats["successful"] += 1
                download_stats["downloaded_files"].append(result["file_name"])
                if result.get("retry_count", 0) > 0:
                    print(f"   ✅ {result['file_name']} 重试 {result['retry_count']} 次后成功")
            else:
                download_stats["failed"] += 1
                download_stats["failed_files"].append({
                    "name": result["file_name"],
                    "reason": result["error"],
                    "retry_count": result.get("retry_count", 0)
                })
        
        # 显示批量下载摘要
        print_batch_download_summary(download_stats)
        
        # 最终更新统一报告文件（包含完整信息）
        await finalize_unified_report(download_stats, report_filepath)
        
    except Exception as e:
        print(f"❌ 批量下载过程出错: {e}")
        import traceback
        traceback.print_exc()


def is_safe_download_operation(file_name):
    """安全检查 - 确保只进行下载操作"""
    try:
        # 检查文件名是否安全
        if not file_name or len(file_name.strip()) == 0:
            return False
        
        # 检查文件扩展名 - 只允许 .zip 文件
        if not file_name.lower().endswith('.zip'):
            return False
        
        # 检查文件名是否包含危险字符
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        for char in dangerous_chars:
            if char in file_name:
                return False
        
        # 检查文件名长度
        if len(file_name) > 255:
            return False
        
        return True
        
    except Exception:
        return False


def print_batch_download_summary(stats):
    """打印批量下载摘要"""
    print(f"\n📊 流水线式并行下载摘要:")
    print("=" * 50)
    print(f"📦 总文件数: {stats['total_files']}")
    print(f"⚡ 最大并发数: {stats['concurrency']}")
    print(f"⏱️ 任务间隔: 5秒")
    print(f"✅ 成功下载: {stats['successful']}")
    print(f"❌ 下载失败: {stats['failed']}")
    
    success_rate = (stats['successful'] / stats['total_files'] * 100) if stats['total_files'] > 0 else 0
    print(f"📈 成功率: {success_rate:.1f}%")
    
    if stats['downloaded_files']:
        print(f"\n✅ 成功下载的文件:")
        for file_name in stats['downloaded_files']:
            print(f"   - {file_name}")
        
        # 显示解压信息
        extracted_count = 0
        extract_task_count = 0
        directory_created_count = 0
        for file_detail in stats.get('file_details', []):
            if file_detail.get('extract_info') and file_detail['extract_info'].get('success'):
                extracted_count += 1
                extract_info = file_detail['extract_info']
                print(f"     📦 已解压: {extract_info['extracted_count']}/{extract_info['total_files_in_zip']} 个文件")
                if extract_info.get('directory_structure_created'):
                    directory_created_count += 1
                    print(f"     📁 目录结构: {extract_info['extract_path']}")
            elif file_detail.get('extract_task_running'):
                extract_task_count += 1
                print(f"     📦 解压中: {file_detail['file_name']}")
        
        if extracted_count > 0:
            print(f"\n📦 解压摘要: {extracted_count} 个zip文件已解压")
        if directory_created_count > 0:
            print(f"📁 目录结构: {directory_created_count} 个原始目录结构已创建")
        if extract_task_count > 0:
            print(f"📦 后台解压: {extract_task_count} 个zip文件正在解压中")
    
    if stats['failed_files']:
        print(f"\n❌ 下载失败的文件:")
        for failed_file in stats['failed_files']:
            retry_info = f" (重试 {failed_file.get('retry_count', 0)} 次)" if failed_file.get('retry_count', 0) > 0 else ""
            print(f"   - {failed_file['name']} ({failed_file['reason']}){retry_info}")
    
    print("=" * 50)


async def save_unified_batch_download_report(stats):
    """保存统一的批量下载报告 - 包含所有文件详情和目录结构"""
    try:
        # 创建logs目录
        logs_dir = Path("downloads/logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成报告文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"unified_batch_download_report_{timestamp}.json"
        report_filepath = logs_dir / report_filename
        
        # 构建完整的报告数据
        report_data = {
            "report_info": {
                "timestamp": stats["timestamp"],
                "report_type": "unified_batch_download",
                "concurrency": stats["concurrency"]
            },
            "summary": {
                "total_files": stats["total_files"],
                "successful_downloads": stats["successful"],
                "failed_downloads": stats["failed"],
                "success_rate": f"{(stats['successful'] / stats['total_files'] * 100):.1f}%" if stats['total_files'] > 0 else "0%"
            },
            "downloaded_files": stats["downloaded_files"],
            "failed_files": stats["failed_files"],
            "file_details": stats["file_details"],
            "task_status_summary": {
                "completed": len([f for f in stats["file_details"] if f.get("status") == "completed"]),
                "failed": len([f for f in stats["file_details"] if f.get("status") == "failed"]),
                "retrying": len([f for f in stats["file_details"] if "retrying" in f.get("status", "")]),
                "downloading": len([f for f in stats["file_details"] if f.get("status") == "downloading"])
            },
            "security_compliance": {
                "only_zip_files": True,
                "safe_operations_only": True,
                "no_dangerous_actions": True,
                "parallel_download_controlled": True
            }
        }
        
        # 保存报告
        with open(report_filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"📋 统一批量下载报告已保存到: {report_filepath}")
        
        # 同时更新主下载状态文件
        await update_main_download_state_with_batch_results(stats)
        
    except Exception as e:
        print(f"❌ 保存统一批量下载报告失败: {e}")


async def update_main_download_state_with_batch_results(stats):
    """更新主下载状态文件，添加批量下载结果"""
    try:
        # 读取现有的下载状态文件
        state_file = Path("downloads/download_state.json")
        if state_file.exists():
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
        else:
            state_data = {"tasks": {}, "timestamp": ""}
        
        # 添加批量下载结果
        state_data["batch_download_results"] = {
            "timestamp": stats["timestamp"],
            "total_files": stats["total_files"],
            "concurrency": stats["concurrency"],
            "successful": stats["successful"],
            "failed": stats["failed"],
            "downloaded_files": stats["downloaded_files"],
            "failed_files": stats["failed_files"]
        }
        
        state_data["timestamp"] = datetime.now().isoformat()
        
        # 保存更新后的状态文件
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, ensure_ascii=False, indent=2)
        
        print(f"📝 已更新主下载状态文件，添加批量下载结果")
        
    except Exception as e:
        print(f"❌ 更新主下载状态文件失败: {e}")


class SharePointExistingBrowserScannerCDP:
    """SharePoint 文件结构扫描器（CDP 监控版） - 业务逻辑封装"""
    
    def __init__(self, test_mode: bool = True, debug_port: int = 9222):
        self.test_mode = test_mode
        self.debug_port = debug_port
        self.scanner = SharePointScanner(test_mode, debug_port)
        self.recursive_scanner = None
        self.downloader = None
        self.status_manager = None
        self.download_monitor = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        playwright = await async_playwright().start()
        success = await self.scanner.connect_to_browser(playwright)
        if success:
            self.recursive_scanner = SharePointRecursiveScanner(self.scanner)
            self.downloader = SharePointFileDownloader(self.scanner.safety_manager)
            self.status_manager = create_download_status_manager("downloads/download_state.json")
            self.download_monitor = BrowserDownloadMonitor(self.status_manager)
            return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.scanner.cleanup_pages()
        await self.scanner.disconnect()
        if self.status_manager:
            self.status_manager.close()
    
    async def wait_for_login_and_scan(self, url: str, recursive: bool = True):
        """等待用户登录并扫描 SharePoint 文件结构"""
        print(f"🔍 开始扫描 SharePoint 文件结构")
        print(f"   目标路径: {url.split('/')[-1] if '/' in url else url}")
        print(f"   测试模式: {'启用' if self.test_mode else '禁用'}")
        print()
        
        page = None
        try:
            # 解析 URL 路径信息
            path_info = self.scanner.safety_manager.parse_sharepoint_url(url)
            self.scanner.scan_results["target_url"] = url
            self.scanner.scan_results["path_info"] = path_info
            
            # 创建新标签页
            page = await self.scanner.context.new_page()
            self.scanner.created_pages.append(page)
            
            # 导航到页面
            if not await navigate_to_url(page, url):
                raise Exception("页面导航失败")
            
            # 获取页面信息
            page_info = await get_page_info(page)
            self.scanner.scan_results["debug_info"]["page_info"].update(page_info)
            
            # 检查是否需要登录
            await check_login_required(page)
            
            # 开始递归扫描
            if recursive:
                await self.recursive_scanner.recursive_scan_folders(page, url, current_path="")
            else:
                # 只扫描当前页面
                elements = await self.scanner.scan_page_elements(page)
                for element in elements:
                    if not element['visible'] or not element['text']:
                        continue
                    element_type = self.scanner.classify_element(element)
                    if element_type == "folder":
                        self.scanner.scan_results["folders"].append({
                            "name": element['text'],
                            "type": "folder",
                            "position": element['position'],
                            "href": element['href'],
                            "index": len(self.scanner.scan_results["folders"])
                        })
                    elif element_type == "file":
                        self.scanner.scan_results["files"].append({
                            "name": element['text'],
                            "type": "file",
                            "position": element['position'],
                            "href": element['href'],
                            "index": len(self.scanner.scan_results["files"])
                        })
            
            # 更新扫描状态
            self.scanner.scan_results["scan_status"] = "completed"
            self.scanner.scan_results["total_items"] = len(self.scanner.scan_results["folders"]) + len(self.scanner.scan_results["files"])
            
            print(f"\n✅ 扫描完成")
            print(f"   发现: {len(self.scanner.scan_results['folders'])} 个文件夹, {len(self.scanner.scan_results['files'])} 个文件")
            
            return self.scanner.scan_results
            
        except Exception as e:
            print(f"❌ 扫描失败: {e}")
            self.scanner.scan_results["scan_status"] = "failed"
            self.scanner.scan_results["error"] = str(e)
            return self.scanner.scan_results
        finally:
            # 确保关闭新创建的标签页，但保留至少一个标签页以维持浏览器运行
            if page and not page.is_closed():
                try:
                    if self.scanner.context and len(self.scanner.context.pages) > 1:
                        await page.close()
                        print("📄 新标签页已关闭")
                    else:
                        print("⚠️ 检测到只有一个标签页，保留以维持浏览器运行")
                        print(f"📄 保留标签页: {page.url}")
                except Exception as e:
                    print(f"⚠️ 关闭标签页时出错: {e}")
    
    async def cleanup_pages(self):
        """手动清理所有新创建的标签页"""
        await self.scanner.cleanup_pages()
    
    def save_results(self, output_file: str = "sharepoint_structure_scan.json"):
        """保存扫描结果"""
        self.scanner.save_results(output_file)


async def batch_download_zip_files():
    """批量下载 .zip 文件（CDP 监控）"""
    print("📦 批量下载 .zip 文件")
    print("=" * 50)
    print("🔒 安全提醒：本脚本严格遵循 SharePoint 安全操作指南")
    print("   ✅ 只允许下载操作")
    print("   ❌ 严格禁止删除、移动、重命名等危险操作")
    print("   🛡️ 所有操作都在安全监控下进行")
    print("   📊 下载状态由浏览器下载器 (CDP) 实时监控")
    print("   📦 支持批量下载多个 .zip 文件")
    print("=" * 50)
    
    async with SharePointExistingBrowserScannerCDP(test_mode=True, debug_port=9222) as scanner:
        try:
            # 获取页面对象
            if scanner.scanner.context and scanner.scanner.context.pages:
                # 选择 SharePoint 页面而不是下载页面
                sharepoint_page = None
                for page in scanner.scanner.context.pages:
                    title = await page.title()
                    url = page.url
                    if 'sharepoint.com' in url or 'KOTEI' in title:
                        sharepoint_page = page
                        break
                if not sharepoint_page:
                    sharepoint_page = scanner.scanner.context.pages[0]
                page = sharepoint_page
                print(f"✅ 使用页面: {await page.title()}")
                
                # 附加 CDP 下载监控
                await scanner.download_monitor.attach_to_page(page)
                
                # 等待用户确认
                input("按回车键开始测试右键下载...")
                
                # 使用更通用的文件结构获取方法
                elements = await page.evaluate("""
            () => {
                const getElementInfo = (element, type, selector) => {
                    const rect = element.getBoundingClientRect();
                    
                    // 获取元素路径
                    const getElementPath = (el) => {
                        const path = [];
                        let current = el;
                        while (current && current !== document.body) {
                            let selector = current.tagName.toLowerCase();
                            if (current.id) {
                                selector += '#' + current.id;
                            } else if (current.className) {
                                const classes = current.className.split(' ').filter(c => c.length > 0);
                                if (classes.length > 0) {
                                    selector += '.' + classes.slice(0, 2).join('.');
                                }
                            }
                            path.unshift(selector);
                            current = current.parentElement;
                        }
                        return path.join(' > ');
                    };
                    
                    return {
                        text: (element.textContent || "").trim(),
                        tagName: element.tagName.toLowerCase(),
                        className: element.className || '',
                        id: element.id || '',
                        href: element.href || '',
                        visible: rect.width > 0 && rect.height > 0,
                        position: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
                        type: type,
                        title: element.title || '',
                        ariaLabel: element.getAttribute('aria-label') || '',
                        foundBySelector: selector,
                        elementPath: getElementPath(element)
                    };
                };

                const allElements = [];
                const seen = new Set(); // 用于去重
                
                // 只查找 span 标签的元素 - 更精确的文件名定位
                const spanSelectors = [
                    'span.heroTextWithHeroCommandsWrapped2_c5aceefe',
                    'span.field-LinkFilename-htmlGrid_1',
                    'span.hero_c5aceefe',
                    'span[data-automation-id="DetailsRow"]',
                    'span.ms-DetailsRow',
                    'span.ms-List-cell',
                    'span.ms-DetailsList-cell'
                ];
                
                // 检测 span 标签元素
                spanSelectors.forEach(selector => {
                    try {
                        document.querySelectorAll(selector).forEach(el => {
                            if (el.classList.contains('headerRow_e4dc14da')) {
                                return;
                            }
                            
                            const text = el.textContent?.trim();
                            if (text && text.length > 0 && text.length < 100) {
                                // 排除表头文本
                                const headerTexts = ['名称', '修改时间', '修改者', '文件大小', '子文件夹计数', '子项目计数', '创建时间', '创建者'];
                                if (headerTexts.includes(text)) {
                                    return;
                                }
                                
                                // 去重
                                if (seen.has(text)) {
                                    return;
                                }
                                seen.add(text);
                                
                                // 判断类型 - 只处理 .zip 文件
                                let itemType = 'unknown';
                                if (text.match(/^\\d{6}$/) || text.match(/^\\d{4}\\d{2}$/) || text.includes('_走行データ送付')) {
                                    itemType = 'folder_item';
                                } else if (text.toLowerCase().endsWith('.zip')) {
                                    itemType = 'zip_file';
                                } else {
                                    // 跳过非 .zip 文件
                                    return;
                                }
                                
                                allElements.push(getElementInfo(el, itemType, selector));
                            }
                        });
                    } catch (e) {
                        console.log('Selector error:', selector, e);
                    }
                });
                
                return allElements;
            }
        """)
                print(f"找到 {len(elements)} 个元素:")
                for i, element in enumerate(elements):
                    print(f"   {i+1}. {element['text']}")
                    print(f"      类型: {element.get('type', 'unknown')}")
                    print(f"      标签: {element.get('tagName', 'unknown')}")
                    print(f"      类名: {element.get('className', 'none')}")
                    print(f"      ID: {element.get('id', 'none')}")
                    print(f"      可见: {element.get('visible', False)}")
                    print(f"      找到方式: {element.get('foundBySelector', 'unknown')}")
                    print(f"      元素路径: {element.get('elementPath', 'unknown')}")
                    if element.get('href'):
                        print(f"      链接: {element['href']}")
                    print()
                
                if elements:
                    # 批量下载模式 - 符合安全操作指南
                    print(f"\n🔒 批量下载模式 - 严格遵循安全操作指南")
                    print("=" * 60)
                    print("✅ 只允许下载操作")
                    print("❌ 严格禁止删除、移动、重命名等危险操作")
                    print("🛡️ 所有操作都在安全监控下进行")
                    print("=" * 60)
                    
                    # 显示所有找到的 .zip 文件
                    zip_files = [elem for elem in elements if elem.get('type') == 'zip_file']
                    if not zip_files:
                        print("❌ 未找到 .zip 文件")
                        return
                    
                    print(f"\n📦 找到 {len(zip_files)} 个 .zip 文件:")
                    for i, file_elem in enumerate(zip_files):
                        print(f"   {i+1}. {file_elem['text']}")
                    
                    # 单次确认批量下载
                    print(f"\n🎯 将流水线式并行下载所有 {len(zip_files)} 个 .zip 文件")
                    print(f"⚡ 最大并发数: {settings.batch_download_concurrency}")
                    print(f"⏱️ 任务间隔: 5秒")
                    print("⚠️ 安全提醒：即将执行流水线式并行下载操作")
                    print("🔒 严格遵循安全操作指南 - 只允许下载操作")
                    
                    final_confirm = input("确认要开始流水线式并行下载吗? (y/n): ").strip().lower()
                    if final_confirm not in ['y', 'yes', '是']:
                        print("⏭️ 用户取消批量下载")
                        return
                    
                    # 执行并行批量下载
                    await batch_download_files(scanner, page, zip_files)
                else:
                    print("❌ 未找到可测试的元素")
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """主函数"""
    # 目标 URL（与原脚本一致）
    target_url = "https://scautoeng.sharepoint.com/sites/KOTEI-SCAE/Shared%20Documents/Forms/AllItems.aspx?id=%2Fsites%2FKOTEI%2DSCAE%2FShared%20Documents%2FGEN1%2E5%E4%B8%AD%E5%9B%BDFOT%2F%E3%83%87%E3%83%BC%E3%82%BF%E8%A7%A3%E6%9E%90%2F%E8%AA%8D%E8%AD%98%E7%B3%BB%2F%E8%B5%B0%E8%B7%AF%E8%AA%8D%E8%AD%98%2F%E3%82%B9%E3%82%AF%E3%83%AA%E3%83%97%E3%83%88%E6%A4%9C%E8%A8%8E%2FTest&viewid=8e19c37a%2Dacdb%2D4c40%2Da22e%2D92e27e7e3366&csf=1&web=1&e=NWcbWt&FolderCTID=0x01200090D0082931AED242A8680C59FF4AF68D"
    
    print("🚀 SharePoint 文件结构扫描器 (使用现有浏览器)")
    print("=" * 60)
    print("🔒 安全提醒：本脚本严格遵循 SharePoint 安全操作指南")
    print("   ✅ 只允许查看、预览、下载等只读操作")
    print("   ❌ 严格禁止删除、移动、重命名等危险操作")
    print("   🛡️ 测试模式下所有操作都需要用户确认")
    print("   📊 下载状态由浏览器下载器 (CDP) 实时监控")
    print("=" * 60)
    
    async with SharePointExistingBrowserScannerCDP(test_mode=True, debug_port=9222) as scanner:
        try:
            # 执行递归扫描
            results = await scanner.wait_for_login_and_scan(target_url, recursive=True)
            # 保存结果
            scanner.save_results()
        finally:
            # 确保清理所有新创建的标签页
            await scanner.cleanup_pages()
        
        # 显示最终结果
        if results['scan_status'] == 'completed':
            print(f"\n✅ 扫描完成")
            print(f"   发现: {len(scanner.scanner.scan_results['folders'])} 个文件夹, {len(scanner.scanner.scan_results['files'])} 个文件")
            
            # 提供下载选项
            if scanner.scanner.scan_results["downloadable_files"]:
                print(f"   可下载文件: {len(scanner.scanner.scan_results['downloadable_files'])} 个")
                download_choice = input("\n是否开始下载文件? (y/n): ").strip().lower()
                if download_choice == 'y':
                    # 获取页面对象用于下载
                    if scanner.scanner.context and scanner.scanner.context.pages:
                        page = scanner.scanner.context.pages[0]
                        # 在触发下载前附加 CDP 监控
                        await scanner.download_monitor.attach_to_page(page)
                        # 触发下载（原逻辑不变，CDP 负责状态与进度）
                        await scanner.downloader.download_files_interactive(page, scanner.scanner.scan_results["downloadable_files"])
                        # 显示下载摘要（可与 DownloadStatusManager 合并使用）
                        download_summary = scanner.downloader.get_download_summary()
                        print(f"\n📊 下载完成: {download_summary['successful_downloads']}/{download_summary['total_downloads']} 成功")
                    else:
                        print("❌ 无法获取页面对象进行下载")
        else:
            print(f"\n❌ 扫描失败: {results.get('error', '未知错误')}")


if __name__ == "__main__":
    import sys
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        asyncio.run(batch_download_zip_files())
    else:
        asyncio.run(main())



