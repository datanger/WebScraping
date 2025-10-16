# 日志重命名最终修复

## 🔍 **问题分析**

用户反馈：
1. **生成了两个日志文件夹**：
   - `20250915_113652` - 包含完整的拷贝日志内容
   - `3NRV1_20250826_113652` - 新创建的，内容不完整

2. **需求**：
   - 只保留一个日志文件夹
   - 使用 `20250915_113652` 的内容（完整内容）
   - 重命名为 `RV1_20250826`（车号_Vector日期，只到日级别）

## ✅ **修复方案**

### 核心思路
- **重命名现有日志文件夹**：不创建新的，直接重命名现有的
- **简化命名格式**：只使用车号和Vector日期，不包含时间
- **保留完整内容**：确保重命名后内容不变

## 🔧 **修改的文件**

### 1. **`data_copy_modules/logging_utils/copy_logger.py`**

#### A. 修改 `rename_log_files_with_vector_date` 函数
```python
def rename_log_files_with_vector_date(vector_date: str, vehicle_number: str = None, group_type: str = None):
    # 提取车号模型 (e.g., "3NRV1" -> "RV1")
    vehicle_model = None
    if vehicle_number:
        import re
        match = re.search(r'3N([A-Z]+\d+)', vehicle_number)
        if match:
            vehicle_model = match.group(1)
    
    # 构建新的日志目录名称（只到日级别，不包含时间）
    if vehicle_model:
        new_log_dir_name = f"{vehicle_model}_{vector_date}"  # 例如: "RV1_20250826"
    else:
        new_log_dir_name = f"{vector_date}"
    
    # 移动现有日志目录到新名称
    shutil.move(LOG_DIR, new_log_subdir)
    
    # 保持原始文件名不变
    COPY_LOG_FILE = os.path.join(new_log_subdir, "datacopy.txt")
    FILELIST_LOG_FILE = os.path.join(new_log_subdir, "filelist.txt")
```

### 2. **`data_copy_modules/interactive_main.py`**

#### A. 恢复拷贝完成后的日志重命名逻辑
```python
# 在Vector logs重命名后，重命名日志目录
if vector_date:
    print(f"✅ Vector logs folder renamed successfully, using date: {vector_date}")
    
    # 重命名日志目录使用Vector日期
    print("🔄 Renaming log directory to use Vector date...")
    success = rename_log_files_with_vector_date(vector_date, vehicle_number)
    if success:
        print("✅ Log directory renamed to use Vector date")
```

#### B. 移除早期日志初始化中的Vector日期逻辑
```python
# 不再在初始化时使用Vector日期，保持原有逻辑
copy_log_file, filelist_log_file = setup_copy_logger(vehicle_number, group_type)
```

## 📋 **工作流程**

### 修复后的流程
1. **日志初始化**：使用当前日期创建日志文件（如 `20250915_113652`）
2. **拷贝进行**：正常记录所有拷贝操作
3. **拷贝完成**：重命名Vector logs文件夹
4. **获取Vector日期**：从Vector logs获取实际日期（如 `20250826`）
5. **重命名日志目录**：将 `20250915_113652` 重命名为 `RV1_20250826`
6. **完成**：只保留一个日志目录，包含完整内容

## 🎯 **修复效果**

### 修复前
```
logs/
├── 20250915_113652/          # 完整内容
│   ├── datacopy.txt (55行)
│   └── filelist.txt (66行)
└── 3NRV1_20250826_113652/    # 不完整内容
    ├── 3NRV1_datacopy.txt (16行)
    └── 3NRV1_filelist.txt (0行)
```

### 修复后
```
logs/
└── RV1_20250826/             # 完整内容，正确命名
    ├── datacopy.txt (55行)
    └── filelist.txt (66行)
```

## 🧪 **手动处理工具**

创建了 `rename_current_logs.py` 脚本来处理当前的日志文件夹：
```bash
python rename_current_logs.py
```

**注意**：如果文件被占用（如IDE打开），需要先关闭相关文件再运行脚本。

## 📝 **命名规则**

- **格式**：`{车号模型}_{Vector日期}`
- **示例**：
  - `3NRV1` → `RV1`
  - Vector日期：`20250826`
  - 最终名称：`RV1_20250826`

## ⚠️ **注意事项**

1. **文件占用**：重命名前确保日志文件没有被其他程序打开
2. **内容完整**：重命名操作不会影响日志文件内容
3. **唯一性**：确保目标目录名称不存在，避免冲突
4. **错误处理**：所有操作都有适当的异常处理

## 🔄 **下次运行效果**

下次运行拷贝程序时，将自动：
1. 创建临时日志目录（如 `20250915_113652`）
2. 记录完整拷贝过程
3. 拷贝完成后自动重命名为 `RV1_20250826`
4. 只保留一个正确命名的日志目录
