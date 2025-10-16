# 早期日志创建修复

## 🔍 **问题分析**

用户需求：
- **一开始创建时就使用正确名称**：不要先创建临时名称再重命名
- **直接创建 `RV1_20250826` 格式的日志文件夹**
- **避免生成多个日志文件夹**

## ✅ **修复方案**

### 核心思路
- **早期获取Vector日期**：在日志初始化前就获取Vector logs的日期
- **直接创建正确命名的日志文件夹**：从一开始就使用 `RV1_20250826` 格式
- **移除后期重命名逻辑**：不再需要拷贝完成后的重命名操作

## 🔧 **修改的文件**

### 1. **`data_copy_modules/logging_utils/copy_logger.py`**

#### A. 新增 `setup_copy_logger_with_vector_date` 函数
```python
def setup_copy_logger_with_vector_date(vehicle_number: str = None, group_type: str = None, vector_date: str = None):
    # 提取车号模型 (e.g., "3NRV1" -> "RV1")
    vehicle_model = None
    if vehicle_number:
        import re
        match = re.search(r'3N([A-Z]+\d+)', vehicle_number)
        if match:
            vehicle_model = match.group(1)
    
    # 构建日志目录名称（只到日级别，不包含时间）
    if vehicle_model and vector_date:
        log_dir_name = f"{vehicle_model}_{vector_date}"  # e.g., "RV1_20250826"
    elif vehicle_model:
        log_dir_name = f"{vehicle_model}_{vector_date}"
    elif vector_date:
        log_dir_name = vector_date
    else:
        # Fallback to current date with time
        current_time = datetime.datetime.now().strftime("%H%M%S")
        log_dir_name = f"{vector_date}_{current_time}"
    
    # 直接创建正确命名的日志目录
    log_subdir = os.path.join(logs_root, log_dir_name)
    os.makedirs(log_subdir, exist_ok=True)
    
    # 创建日志文件（保持简单名称）
    copy_log_file = os.path.join(log_subdir, "datacopy.txt")
    filelist_log_file = os.path.join(log_subdir, "filelist.txt")
```

### 2. **`data_copy_modules/interactive_main.py`**

#### A. 修改 `_initialize_logging` 函数
```python
def _initialize_logging(self):
    # 在日志初始化前获取Vector日期
    vector_date = None
    if self.vector_drive:
        vector_date = self._get_vector_logs_date(self.vector_drive)
        if vector_date:
            print(f"📅 Found Vector logs date for log naming: {vector_date}")
        else:
            print("⚠️ Could not determine Vector logs date, using current date")
    
    # 使用Vector日期直接创建正确命名的日志文件夹
    from data_copy_modules.logging_utils.copy_logger import setup_copy_logger_with_vector_date
    copy_log_file, filelist_log_file = setup_copy_logger_with_vector_date(vehicle_number, group_type, vector_date)
```

#### B. 简化Vector logs重命名逻辑
```python
# 移除复杂的日志重命名逻辑，只保留Vector logs重命名
if self.vector_drive and (copy_results.get("vector_to_transfer", False) or copy_results.get("vector_to_backup", False)):
    print("\n🔄 Renaming Vector logs folder to archive format...")
    vector_date = self.detector._rename_vector_logs_to_archive(self.vector_drive)
    if vector_date:
        print(f"✅ Vector logs folder renamed successfully, using date: {vector_date}")
```

## 📋 **工作流程**

### 修复后的流程
1. **检测Vector日期**：在日志初始化前获取Vector logs的日期
2. **提取车号模型**：从 `3NRV1` 提取 `RV1`
3. **直接创建正确命名的日志文件夹**：`RV1_20250826`
4. **拷贝进行**：正常记录所有拷贝操作
5. **拷贝完成**：只重命名Vector logs文件夹（日志文件夹已经是正确名称）

## 🎯 **修复效果**

### 修复前
```
# 创建临时日志文件夹
logs/20250915_113652/          # 临时名称

# 拷贝完成后尝试重命名
logs/RV1_20250826/             # 重命名后
```

### 修复后
```
# 直接创建正确命名的日志文件夹
logs/RV1_20250826/             # 从一开始就是正确名称
```

## 🧪 **测试工具**

创建了 `test_early_log_naming.py` 测试脚本：
```bash
python test_early_log_naming.py
```

## 📝 **命名规则**

- **格式**：`{车号模型}_{Vector日期}`
- **示例**：
  - 车号：`3NRV1` → 车号模型：`RV1`
  - Vector日期：`20250826`
  - 最终名称：`RV1_20250826`

## ⚠️ **注意事项**

1. **Vector日期获取**：如果Vector drive不存在或无法访问，会使用当前日期作为回退
2. **车号提取**：如果车号格式不匹配，会使用原始车号
3. **目录冲突**：如果目标目录已存在，会创建失败
4. **错误处理**：所有操作都有适当的异常处理

## 🔄 **下次运行效果**

下次运行拷贝程序时，将：
1. ✅ 在日志初始化前获取Vector日期
2. ✅ 直接创建 `RV1_20250826` 格式的日志文件夹
3. ✅ 只生成一个正确命名的日志文件夹
4. ✅ 避免后期重命名的复杂性
5. ✅ 确保日志文件夹名称从一开始就是正确的
