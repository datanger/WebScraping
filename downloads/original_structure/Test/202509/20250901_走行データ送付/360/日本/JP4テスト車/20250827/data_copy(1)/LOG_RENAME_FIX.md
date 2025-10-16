# 日志重命名和错误修复

## 🔍 **问题分析**

根据用户反馈，发现两个问题：

1. **报错**：`Could not log rename operation: No module named 'data_copy_modules'`
2. **日志文件命名**：需要使用Vector logs文件夹的修改日期，而不是当前日期

## ✅ **修复方案**

### 1. **修复重命名操作的日志记录错误**

**问题**：导入模块路径错误导致日志记录失败

**修复**：在 `data_copy_modules/core/system_detector.py` 中修复导入逻辑
```python
# 修复前
from data_copy_modules.logging_utils.copy_logger import log_copy_operation

# 修复后
try:
    from logging_utils.copy_logger import log_copy_operation
except ImportError:
    try:
        from data_copy_modules.logging_utils.copy_logger import log_copy_operation
    except Exception as e:
        logger.warning(f"Could not log rename operation: {e}")
```

### 2. **修改日志文件命名逻辑**

**需求**：日志文件要以车号和日期进行命名，日期使用Vector logs文件夹的修改日期

**实现方案**：

#### A. 修改 `setup_copy_logger` 函数
- 添加 `vector_date` 参数
- 如果提供Vector日期，使用该日期而不是当前日期

#### B. 新增 `rename_log_files_with_vector_date` 函数
- 在Vector logs重命名后，重新命名日志文件
- 使用Vector logs的日期作为日志文件命名

#### C. 修改Vector logs重命名逻辑
- 返回使用的日期信息
- 在拷贝完成后重新命名日志文件

## 🔧 **修改的文件**

### 1. **`data_copy_modules/logging_utils/copy_logger.py`**

#### A. 修改 `setup_copy_logger` 函数
```python
def setup_copy_logger(vehicle_number: str = None, group_type: str = None, vector_date: str = None):
    # 使用vector_date如果提供，否则使用当前日期
    if vector_date:
        log_date = vector_date
        print(f"📅 Using Vector logs date for log naming: {log_date}")
    else:
        log_date = datetime.datetime.now().strftime("%Y%m%d")
        print(f"📅 Using current date for log naming: {log_date}")
```

#### B. 新增 `rename_log_files_with_vector_date` 函数
```python
def rename_log_files_with_vector_date(vector_date: str, vehicle_number: str = None, group_type: str = None):
    # 重新命名日志目录和文件，使用Vector日期
    # 移动日志目录到新的名称
    # 更新全局变量
```

### 2. **`data_copy_modules/core/system_detector.py`**

#### A. 修复导入错误
```python
# 修复重命名操作的日志记录导入问题
try:
    from logging_utils.copy_logger import log_copy_operation
except ImportError:
    try:
        from data_copy_modules.logging_utils.copy_logger import log_copy_operation
    except Exception as e:
        logger.warning(f"Could not log rename operation: {e}")
```

#### B. 修改返回值
```python
# 返回使用的日期信息，而不是布尔值
return earliest_date  # 而不是 return True
```

### 3. **`data_copy_modules/interactive_main.py`**

#### A. 修改Vector logs重命名后的处理逻辑
```python
# 获取Vector日期
vector_date = self.detector._rename_vector_logs_to_archive(self.vector_drive)
if vector_date:
    # 重新命名日志文件使用Vector日期
    success = rename_log_files_with_vector_date(vector_date, vehicle_number, group_type)
```

## 📋 **修复效果**

### 修复前
```
# 错误信息
Could not log rename operation: No module named 'data_copy_modules'

# 日志文件命名
logs/20250915_111921/datacopy.txt  # 使用当前日期
```

### 修复后
```
# 无错误信息
✅ Vector logs folder renamed successfully, using date: 20250827
✅ Log files renamed to use Vector date

# 日志文件命名
logs/3NRV1_A组_20250827_111921/3NRV1_A组_datacopy.txt  # 使用Vector日期
```

## 🎯 **工作流程**

1. **拷贝开始**：使用当前日期创建日志文件
2. **拷贝进行**：正常记录所有拷贝操作
3. **拷贝完成**：重命名Vector logs文件夹
4. **获取日期**：从Vector logs文件夹获取实际日期
5. **重命名日志**：将日志文件重命名为使用Vector日期
6. **完成**：日志文件名称反映实际的数据日期

## 📝 **注意事项**

- 日志重命名不会影响正在进行的日志记录
- 如果Vector logs重命名失败，日志文件保持原名称
- 支持车号和组别信息的完整日志命名
- 所有错误都有适当的异常处理
