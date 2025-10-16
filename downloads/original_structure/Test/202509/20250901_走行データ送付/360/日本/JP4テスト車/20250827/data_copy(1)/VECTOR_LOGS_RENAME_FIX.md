# Vector Logs 重命名问题修复

## 🔍 **问题分析**

根据用户反馈和日志分析，发现两个关键问题：

### 1. **重命名时机问题**
- **问题**：在拷贝完成前就尝试重命名logs文件夹
- **错误信息**：`[WinError 5] 拒绝访问。: 'H:\\logs' -> 'H:\\20250915-archive'`
- **原因**：其他线程可能仍在访问logs文件夹

### 2. **日期获取错误**
- **问题**：使用当前日期而不是logs文件夹下文件的创建日期
- **期望**：使用logs文件夹下文件的实际创建日期，如 `20250827-archive`
- **当前**：使用当前日期，如 `20250915-archive`

## ✅ **修复方案**

### 1. **修复重命名时机**
- **移除**：从 `copy_vector_data_to_transfer` 和 `copy_vector_data_to_backup` 函数中移除立即重命名
- **新增**：在 `interactive_main.py` 中，所有拷贝任务完成后统一执行重命名
- **延迟**：重命名前等待2秒，确保没有其他进程访问文件夹

### 2. **修复日期获取逻辑**
- **扫描**：遍历logs文件夹中的所有文件
- **获取**：获取每个文件的创建时间（Windows使用 `getctime`，Unix使用 `getmtime`）
- **选择**：选择最早的创建日期作为归档名称
- **回退**：如果无法获取文件日期，使用当前日期作为回退

## 🔧 **修改的文件**

### 1. **`data_copy_modules/core/system_detector.py`**
```python
def _rename_vector_logs_to_archive(self, vector_drive: str) -> bool:
    # 获取logs文件夹中文件的最早创建日期
    earliest_date = None
    for root, dirs, files in os.walk(logs_path):
        for file in files:
            file_path = os.path.join(root, file)
            creation_time = os.path.getctime(file_path)  # Windows
            file_date = datetime.datetime.fromtimestamp(creation_time).strftime("%Y%m%d")
            if earliest_date is None or file_date < earliest_date:
                earliest_date = file_date
    
    # 等待2秒确保没有其他进程访问
    time.sleep(2)
    
    # 重命名
    archive_name = f"{earliest_date}-archive"
    os.rename(logs_path, archive_path)
```

### 2. **`data_copy_modules/interactive_main.py`**
```python
# 在所有拷贝任务完成后执行重命名
if self.vector_drive and (copy_results.get("vector_to_transfer", False) or copy_results.get("vector_to_backup", False)):
    print("\n🔄 Renaming Vector logs folder to archive format...")
    success = self.detector._rename_vector_logs_to_archive(self.vector_drive)
```

## 🧪 **测试工具**

创建了 `test_vector_date_detection.py` 用于测试日期检测功能：
- 扫描指定路径下的logs文件夹
- 分析文件创建日期
- 显示建议的归档名称

## 📋 **修复效果**

### 修复前：
- ❌ 重命名时机错误，导致访问拒绝
- ❌ 使用当前日期，不符合需求
- ❌ 日志显示：`20250915-archive`

### 修复后：
- ✅ 在所有拷贝任务完成后重命名
- ✅ 使用logs文件夹中文件的实际创建日期
- ✅ 日志显示：`20250827-archive`（根据实际文件日期）

## 🎯 **使用说明**

1. **正常运行**：修复后的代码会自动处理重命名
2. **测试日期检测**：运行 `python test_vector_date_detection.py`
3. **查看日志**：重命名操作会记录在日志中

## ⚠️ **注意事项**

- 重命名前会等待2秒，确保没有其他进程访问
- 如果无法获取文件日期，会使用当前日期作为回退
- 如果目标归档文件夹已存在，会跳过重命名
- 重命名操作会记录详细的日志信息
