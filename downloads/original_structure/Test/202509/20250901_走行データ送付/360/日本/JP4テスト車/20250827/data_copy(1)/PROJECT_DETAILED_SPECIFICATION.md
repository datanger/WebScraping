# 数据拷贝工具详细工程说明

## 项目概述

本项目是一个跨平台的数据拷贝工具，专门用于处理车载数据采集系统中的多盘符数据拷贝任务。支持Qdrive（201/203/230/231）和Vector数据盘的自动识别、拷贝、验证和日志记录。

## 核心功能模块

### 1. 系统架构

```
data_copy_modules/
├── core/                    # 核心检测模块
│   └── system_detector.py   # 跨平台系统检测器
├── data_copy/               # 数据处理模块
│   ├── qdrive_data_handler.py    # Qdrive数据处理
│   └── vector_data_handler.py    # Vector数据处理
├── drivers/                 # 驱动管理模块
│   ├── bitlocker_manager.py      # BitLocker管理
│   └── drive_detector.py         # 盘符检测
├── logging_utils/           # 日志管理模块
│   └── copy_logger.py            # 拷贝日志记录
├── utils/                   # 工具模块
│   ├── detailed_progress.py      # 详细进度跟踪
│   ├── file_utils.py             # 文件操作工具
│   ├── progress_bar.py           # 进度条显示
│   └── confirmation_interface.py # 确认界面
├── config_manager.py        # 配置管理
└── interactive_main.py      # 交互式主程序
```

### 2. 配置管理系统

#### 2.1 配置文件结构 (`copy_config.ini`)

```ini
[PERFORMANCE]
# 性能模式：fast/balanced/safe
performance_mode = fast
# 最大并发线程数
max_concurrent_threads = 8
# 文件缓冲区大小（字节）
file_buffer_size = 16777216
# 进度更新间隔（秒）
progress_update_interval = 10
# 验证容差（字节）
verification_tolerance = 2048

[VEHICLE]
# 预期车型（RV1/RV2等）
expected_vehicle_model = RV1
# 严格车型验证
strict_vehicle_validation = true

[LOGGING]
# 日志级别
log_level = INFO
# 详细进度日志
detailed_progress_logging = true
# 文件拷贝日志
file_copy_logging = false

[COPY_OPTIONS]
# 跳过已存在文件
skip_existing_files = false
# 文件完整性验证
verify_file_integrity = false
# 最大重试次数
max_retry_attempts = 2
# 重试延迟（秒）
retry_delay = 3

[ADVANCED]
# 实验性功能
enable_experimental_features = false
# 大文件缓冲区（字节）
large_file_buffer_size = 33554432
# 文件操作超时（秒）
file_operation_timeout = 600
```

#### 2.2 配置管理器实现

```python
class ConfigManager:
    """配置管理器类"""
    
    def __init__(self, config_file: str = "copy_config.ini"):
        """初始化配置管理器"""
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self._load_config()
    
    def get_performance_settings(self) -> Dict[str, Any]:
        """获取所有性能相关设置"""
        return {
            'mode': self.get_performance_mode(),
            'max_threads': self.get_max_concurrent_threads(),
            'buffer_size': self.get_file_buffer_size(),
            'update_interval': self.get_progress_update_interval(),
            'verification_tolerance': self.get_verification_tolerance()
        }
    
    def validate_vehicle_model(self, detected_model: str) -> bool:
        """验证检测到的车型是否与预期匹配"""
        expected = self.get_expected_vehicle_model()
        detected = detected_model.upper() if detected_model else ""
        
        if not self.is_strict_vehicle_validation_enabled():
            return True
        
        return expected == detected
```

### 3. 盘符识别系统

#### 3.1 Qdrive识别逻辑

```python
def identify_qdrive_drives(self, external_drives: List[str]) -> List[str]:
    """识别Qdrive盘符"""
    qdrive_drives = []
    
    for drive in external_drives:
        try:
            # 检查data文件夹
            data_path = os.path.join(drive, 'data')
            if not os.path.exists(data_path):
                continue
            
            # 检查2qd_开头的文件夹
            data_items = os.listdir(data_path)
            qdrive_folders = [item for item in data_items 
                            if os.path.isdir(os.path.join(data_path, item)) 
                            and item.startswith('2qd_')]
            
            if qdrive_folders:
                # 提取盘符编号
                folder_name = qdrive_folders[0]
                match = re.search(r'2qd_(\d+)', folder_name)
                if match:
                    drive_number = match.group(1)
                    self.qdrive_number_mapping[drive] = drive_number
                    qdrive_drives.append(drive)
                    
        except Exception as e:
            logger.warning(f"Error checking Qdrive on {drive}: {e}")
    
    return qdrive_drives
```

#### 3.2 Vector识别逻辑

```python
def identify_vector_drives(self, external_drives: List[str]) -> List[str]:
    """识别Vector盘符"""
    vector_drives = []
    
    for drive in external_drives:
        try:
            # 检查logs文件夹
            logs_path = os.path.join(drive, 'logs')
            if not os.path.exists(logs_path):
                continue
            
            # 检查车型文件夹
            logs_items = os.listdir(logs_path)
            vehicle_folders = [item for item in logs_items 
                             if os.path.isdir(os.path.join(logs_path, item))
                             and re.match(r'\d*RV\d+', item)]
            
            if vehicle_folders:
                vector_drives.append(drive)
                
        except Exception as e:
            logger.warning(f"Error checking Vector on {drive}: {e}")
    
    return vector_drives
```

#### 3.3 Transfer/Backup识别逻辑

```python
def identify_transfer_drives(self, external_drives: List[str]) -> List[str]:
    """识别Transfer盘符"""
    transfer_drives = []
    
    for drive in external_drives:
        try:
            volume_name = self.get_volume_name(drive)
            if volume_name and 'transfer' in volume_name.lower():
                transfer_drives.append(drive)
        except Exception:
            pass
    
    return transfer_drives

def identify_backup_drives(self, external_drives: List[str]) -> List[str]:
    """识别Backup盘符"""
    backup_drives = []
    
    for drive in external_drives:
        try:
            volume_name = self.get_volume_name(drive)
            # 严格匹配：Echo开头，backup结尾
            if volume_name and volume_name.startswith('Echo') and volume_name.endswith('backup'):
                backup_drives.append(drive)
        except Exception:
            pass
    
    return backup_drives
```

### 4. 车型验证系统

#### 4.1 车型检测实现

```python
def _detect_vehicle_model_from_vector(self, vector_drive: str) -> str:
    """从Vector盘符检测车型"""
    try:
        logs_path = os.path.join(vector_drive, 'logs')
        if not os.path.exists(logs_path):
            return "UNKNOWN"
        
        # 查找车型目录
        for item in os.listdir(logs_path):
            item_path = os.path.join(logs_path, item)
            if os.path.isdir(item_path):
                # 提取车型（如"3NRV1" -> "RV1"）
                import re
                match = re.search(r'(\d*RV\d+)', item.upper())
                if match:
                    vehicle_code = match.group(1)
                    rv_match = re.search(r'(RV\d+)', vehicle_code)
                    if rv_match:
                        return rv_match.group(1)
        
        return "UNKNOWN"
        
    except Exception as e:
        print(f"Warning: Could not detect vehicle model from Vector drive: {e}")
        return "UNKNOWN"
```

#### 4.2 验证流程

```python
# 在Vector盘符选择后立即验证
if self.vector_drive:
    detected_model = self._detect_vehicle_model_from_vector(self.vector_drive)
    validation_message = self.config_manager.get_vehicle_validation_message(detected_model)
    
    if not self.config_manager.validate_vehicle_model(detected_model):
        print(f"❌ {validation_message}")
        print(f"❌ Copy operation will be aborted due to vehicle model mismatch!")
        return None
```

### 5. 拷贝执行系统

#### 5.1 拷贝计划创建

```python
def create_copy_plan(self) -> Dict[str, bool]:
    """创建拷贝计划"""
    copy_plan = {
        'qdrive_to_transfer': False,
        'qdrive_to_backup': False,
        'vector_to_transfer': False,
        'vector_to_backup': False
    }
    
    # 检查Qdrive拷贝条件
    if self.qdrive_drives and self.transfer_drive:
        copy_plan['qdrive_to_transfer'] = True
    
    if self.qdrive_drives and self.backup_drive:
        copy_plan['qdrive_to_backup'] = True
    
    # 检查Vector拷贝条件
    if self.vector_drive and self.transfer_drive:
        copy_plan['vector_to_transfer'] = True
    
    if self.vector_drive and self.backup_drive:
        copy_plan['vector_to_backup'] = True
    
    return copy_plan
```

#### 5.2 多线程拷贝实现

```python
def execute_copy_plan(self) -> bool:
    """执行拷贝计划"""
    # 初始化进度跟踪器
    perf_settings = self.config_manager.get_performance_settings()
    progress_tracker = get_progress_tracker(refresh_interval=perf_settings['update_interval'])
    
    copy_results = {}
    copy_threads = []
    
    # 1. Qdrive → Transfer
    if self.copy_plan['qdrive_to_transfer']:
        for qdrive_drive in self.qdrive_drives:
            def copy_qdrive_to_transfer():
                try:
                    success = self.detector.copy_qdrive_data_to_transfer(qdrive_drive, self.transfer_drive)
                    copy_results[f"qdrive_{qdrive_drive}_to_transfer"] = success
                except Exception as e:
                    copy_results[f"qdrive_{qdrive_drive}_to_transfer"] = False
            
            thread = threading.Thread(target=copy_qdrive_to_transfer)
            copy_threads.append(thread)
            thread.start()
    
    # 等待所有线程完成
    for thread in copy_threads:
        thread.join(timeout=300)  # 5分钟超时
    
    return all(copy_results.values())
```

### 6. 进度跟踪系统

#### 6.1 详细进度跟踪器

```python
class DetailedProgressTracker:
    """详细进度跟踪器"""
    
    def __init__(self, refresh_interval: int = 30):
        self.tasks = {}
        self.lock = threading.Lock()
        self.refresh_interval = refresh_interval
        self.last_refresh = 0
        self.is_displaying = False
    
    def add_task(self, task_id: str, source: str, destination: str):
        """添加任务"""
        with self.lock:
            self.tasks[task_id] = {
                'source': source,
                'destination': destination,
                'status': 'running',
                'copied_files': 0,
                'total_files': 0,
                'start_time': time.time()
            }
    
    def update_task(self, task_id: str, copied_files: int, total_files: int = None):
        """更新任务进度"""
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id]['copied_files'] = copied_files
                if total_files is not None:
                    self.tasks[task_id]['total_files'] = total_files
                
                # 智能刷新逻辑
                current_time = time.time()
                if (current_time - self.last_refresh >= self.refresh_interval or
                    self._should_refresh_now()):
                    self._display_progress()
                    self.last_refresh = current_time
    
    def _should_refresh_now(self) -> bool:
        """判断是否应该立即刷新"""
        current_time = time.time()
        
        # 检查是否有运行中的任务在最近3分钟内更新
        for task in self.tasks.values():
            if task['status'] == 'running':
                if current_time - task.get('last_update', 0) < 180:  # 3分钟
                    return True
        
        # 检查是否有完成/失败的任务在最近1分钟内更新
        for task in self.tasks.values():
            if task['status'] in ['completed', 'failed']:
                if current_time - task.get('last_update', 0) < 60:  # 1分钟
                    return True
        
        return False
```

#### 6.2 进度显示实现

```python
def _display_progress(self):
    """显示进度"""
    if self.is_displaying:
        return
    
    self.is_displaying = True
    
    try:
        # 清屏并重绘
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 80)
        print("Data Copy Progress")
        print("=" * 80)
        
        # 显示总体进度
        total_tasks = len(self.tasks)
        completed_tasks = sum(1 for task in self.tasks.values() 
                            if task['status'] in ['completed', 'failed'])
        
        if total_tasks > 0:
            overall_progress = (completed_tasks / total_tasks) * 100
            print(f"Overall Progress: {completed_tasks}/{total_tasks} tasks completed ({overall_progress:.1f}%)")
        
        print("-" * 80)
        
        # 显示各任务进度
        for task_id, task in self.tasks.items():
            status_icon = {
                'running': '🔄',
                'completed': '✅',
                'failed': '❌'
            }.get(task['status'], '❓')
            
            if task['total_files'] > 0:
                progress_percent = min((task['copied_files'] / task['total_files']) * 100, 100.0)
                print(f"{status_icon} {task_id:<30} {task['copied_files']}/{task['total_files']} files ({progress_percent:.1f}%)")
            else:
                print(f"{status_icon} {task_id:<30} {task['copied_files']} files")
        
        print("=" * 80)
        
    finally:
        self.is_displaying = False
```

### 7. 文件操作系统

#### 7.1 目录拷贝实现

```python
def copy_directory_with_rename(source_dir: str, dest_dir: str, progress_callback=None) -> bool:
    """带重命名的目录拷贝"""
    try:
        # 获取源目录统计信息
        source_stats = get_directory_stats(source_dir)
        total_files = source_stats['file_count']
        
        if progress_callback:
            progress_callback(0)  # 初始化进度
        
        copied_files = 0
        
        # 遍历源目录
        for root, dirs, files in os.walk(source_dir):
            # 计算相对路径
            rel_path = os.path.relpath(root, source_dir)
            if rel_path == '.':
                dest_path = dest_dir
            else:
                dest_path = os.path.join(dest_dir, rel_path)
            
            # 创建目标目录
            os.makedirs(dest_path, exist_ok=True)
            
            # 拷贝文件
            for file in files:
                source_file = os.path.join(root, file)
                dest_file = os.path.join(dest_path, file)
                
                # 处理重名文件
                dest_file = get_unique_filename(dest_file)
                
                # 拷贝文件
                shutil.copy2(source_file, dest_file)
                copied_files += 1
                
                # 更新进度
                if progress_callback:
                    progress_callback(1)
        
        # 确保进度达到100%
        if progress_callback and copied_files < total_files:
            remaining = total_files - copied_files
            progress_callback(remaining)
        
        return True
        
    except Exception as e:
        logger.error(f"Error copying directory: {e}")
        return False
```

#### 7.2 文件重命名逻辑

```python
def get_unique_filename(file_path: str) -> str:
    """获取唯一文件名"""
    if not os.path.exists(file_path):
        return file_path
    
    base, ext = os.path.splitext(file_path)
    counter = 1
    
    while True:
        new_path = f"{base}_{counter}{ext}"
        if not os.path.exists(new_path):
            return new_path
        counter += 1
```

### 8. 日志记录系统

#### 8.1 日志初始化

```python
def setup_copy_logger_with_vector_date(vehicle_number: str = None, group_type: str = None, vector_date: str = None):
    """使用Vector日期设置拷贝日志器"""
    global copy_logger, COPY_LOG_FILE, FILELIST_LOG_FILE, LOG_DIR
    
    # 创建日志根目录
    logs_root = "logs"
    if not os.path.exists(logs_root):
        os.makedirs(logs_root)
    
    # 构建日志目录名
    if vector_date and vehicle_number:
        # 提取车型（如"3NRV1" -> "RV1"）
        import re
        rv_match = re.search(r'(RV\d+)', vehicle_number.upper())
        vehicle_model = rv_match.group(1) if rv_match else vehicle_number
        log_dir_name = f"{vehicle_model}_{vector_date}"
    else:
        # 使用当前时间
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir_name = current_time
    
    # 创建日志子目录
    log_subdir = os.path.join(logs_root, log_dir_name)
    if not os.path.exists(log_subdir):
        os.makedirs(log_subdir)
    
    LOG_DIR = log_subdir
    
    # 生成日志文件名
    copy_log_file = os.path.join(log_subdir, "datacopy.txt")
    filelist_log_file = os.path.join(log_subdir, "filelist.txt")
    
    # 创建文件处理器
    copy_file_handler = logging.FileHandler(copy_log_file, encoding='utf-8')
    copy_file_handler.setLevel(logging.INFO)
    
    # 设置格式
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    copy_file_handler.setFormatter(formatter)
    
    # 添加处理器
    copy_logger.addHandler(copy_file_handler)
    
    # 更新全局变量
    COPY_LOG_FILE = copy_log_file
    FILELIST_LOG_FILE = filelist_log_file
    
    return copy_log_file, filelist_log_file
```

#### 8.2 文件列表记录

```python
def log_copy_operation(message: str, log_type: str = 'copy', is_error: bool = False):
    """记录拷贝操作"""
    global COPY_LOG_FILE, FILELIST_LOG_FILE
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        if log_type == 'copy' and COPY_LOG_FILE:
            with open(COPY_LOG_FILE, 'a', encoding='utf-8') as f:
                if is_error:
                    f.write(f"{timestamp}: \033[91m{message}\033[0m\n")
                else:
                    f.write(f"{timestamp}: {message}\n")
        elif log_type == 'filelist' and FILELIST_LOG_FILE:
            with open(FILELIST_LOG_FILE, 'a', encoding='utf-8') as f:
                if is_error:
                    f.write(f"\033[91m{message}\033[0m\n")
                else:
                    f.write(f"{message}\n")
    except Exception as e:
        print(f"Error logging operation: {e}")
```

### 9. 完整性验证系统

#### 9.1 四次比对验证

```python
def post_copy_verification(self):
    """拷贝后完整性验证"""
    overall_verified = True
    verification_messages = []
    
    # 1) Qdrive总和 vs Transfer/data
    if self.transfer_drive and self.qdrive_drives:
        q_sum = self._sum_qdrive_sources(self.qdrive_drives)
        t_data = self._safe_stats(os.path.join(self.transfer_drive, 'data'))
        tolerance = self.config_manager.get_verification_tolerance()
        
        ok1 = (q_sum['file_count'] == t_data['file_count'] and
               abs(q_sum['total_size'] - t_data['total_size']) < tolerance)
        overall_verified = overall_verified and ok1
        
        # 记录详细计算过程
        calc_msg = f"Qdrive→Transfer /data calculation:\n"
        for detail in q_sum['details']:
            calc_msg += f"  + {detail}\n"
        calc_msg += f"  = Total: {q_sum['file_count']} files, {q_sum['total_size']} bytes"
        verification_messages.append(calc_msg)
        
        verification_messages.append(f"Qdrive→Transfer /data match: {'OK' if ok1 else 'MISMATCH'}")
    
    # 2) Vector总和 vs Transfer/logs
    if self.transfer_drive and self.vector_drive:
        v_src = self._safe_stats(os.path.join(self.vector_drive, 'logs'))
        t_logs = self._safe_stats(os.path.join(self.transfer_drive, 'logs'))
        ok2 = (v_src['file_count'] == t_logs['file_count'] and
               abs(v_src['total_size'] - t_logs['total_size']) < tolerance)
        overall_verified = overall_verified and ok2
        verification_messages.append(f"Vector→Transfer /logs match: {'OK' if ok2 else 'MISMATCH'}")
    
    # 3) 每个Qdrive vs Backup对应目录
    if self.backup_drive and self.qdrive_drives:
        for d in self.qdrive_drives:
            drive_number = self.qdrive_number_mapping.get(d, 'UNKNOWN')
            src_stats = self._safe_stats(os.path.join(d, 'data'))
            dst_path = self._find_backup_qdrive_data_path(self.backup_drive, drive_number)
            dst_stats = self._safe_stats(dst_path) if dst_path else {'file_count': 0, 'total_size': 0}
            
            ok3 = (src_stats['file_count'] == dst_stats['file_count'] and
                   abs(src_stats['total_size'] - dst_stats['total_size']) < tolerance)
            overall_verified = overall_verified and ok3
            verification_messages.append(f"Qdrive {drive_number}→Backup match: {'OK' if ok3 else 'MISMATCH'}")
    
    # 4) Vector总和 vs Backup logs
    if self.backup_drive and self.vector_drive:
        v_src2 = self._safe_stats(os.path.join(self.vector_drive, 'logs'))
        backup_logs_path = self._find_backup_logs_path(self.backup_drive)
        v_dst2 = self._safe_stats(backup_logs_path)
        
        ok4 = (v_src2['file_count'] == v_dst2['file_count'] and
               abs(v_src2['total_size'] - v_dst2['total_size']) < tolerance)
        overall_verified = overall_verified and ok4
        verification_messages.append(f"Vector→Backup logs match: {'OK' if ok4 else 'MISMATCH'}")
    
    # 记录验证结果到日志
    self._log_verification_results(verification_messages, overall_verified)
    
    return overall_verified
```

#### 9.2 验证结果记录

```python
def _log_verification_results(self, verification_messages: List[str], overall_verified: bool):
    """记录验证结果到日志"""
    try:
        from logging_utils.copy_logger import log_copy_operation
        log_copy_operation("="*80)
        log_copy_operation("Post-copy integrity verification results:")
        for msg in verification_messages:
            log_copy_operation(f" - {msg}")
        log_copy_operation(f"Overall verification status: {'PASSED' if overall_verified else 'FAILED'}")
        log_copy_operation("="*80)
    except Exception as e:
        print(f"Warning: Could not log verification results: {e}")
```

### 10. 重复检测系统

#### 10.1 Vector第三层目录导出

```python
def _export_vector_third_level_dirs(self, vector_drive: str) -> bool:
    """导出Vector第三层目录名到folderstructure.txt"""
    try:
        logs_root = os.path.join(vector_drive, 'logs')
        if not os.path.exists(logs_root):
            return False
        
        third_level_names = []
        
        # 遍历logs/<vehicle>/<date_time>结构
        for vehicle_dir in os.listdir(logs_root):
            vehicle_path = os.path.join(logs_root, vehicle_dir)
            if not os.path.isdir(vehicle_path):
                continue
            
            for dt_dir in os.listdir(vehicle_path):
                dt_path = os.path.join(vehicle_path, dt_dir)
                if os.path.isdir(dt_path):
                    third_level_names.append(dt_dir)
        
        # 排序并去重
        third_level_names = sorted(set(third_level_names))
        
        # 写入folderstructure.txt
        log_dir = self._get_log_directory()
        if log_dir:
            folderstructure_file = os.path.join(log_dir, "folderstructure.txt")
            with open(folderstructure_file, 'w', encoding='utf-8') as f:
                for name in third_level_names:
                    f.write(f"{name}\n")
            
            logger.info(f"Exported {len(third_level_names)} third-level directory names to {folderstructure_file}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error exporting Vector third-level directories: {e}")
        return False
```

#### 10.2 重复检测实现

```python
def check_vector_duplicate_third_level(self, vector_drive: str) -> Tuple[bool, List[str]]:
    """检查Vector第三层目录是否与历史记录重复"""
    try:
        # 获取当前Vector第三层目录名
        current = set(self._get_vector_third_level_names(vector_drive))
        
        # 获取最新的历史记录
        previous = set(self._get_latest_logged_folderstructure())
        
        # 查找重复项
        duplicates = sorted(current.intersection(previous))
        
        return (len(duplicates) > 0, duplicates)
        
    except Exception as e:
        logger.error(f"Error checking Vector duplicate third-level directories: {e}")
        return (False, [])
```

### 11. 数据重命名系统

#### 11.1 Qdrive数据重命名

```python
def _rename_qdrive_data_to_archive(self, qdrive_drive: str, vector_drive: str = None) -> str:
    """将Qdrive data文件夹重命名为日期_archive格式"""
    try:
        data_path = os.path.join(qdrive_drive, 'data')
        if not os.path.exists(data_path):
            return False
        
        # 优先从Vector第三层目录获取日期
        derived_date = None
        if vector_drive:
            try:
                third_level = self._get_vector_third_level_names(vector_drive)
                if third_level:
                    min_name = sorted(third_level)[0]  # 最小日期
                    parts = min_name.split('_')
                    if parts and len(parts[0]) == 8 and parts[0].isdigit():
                        derived_date = parts[0]
            except Exception:
                pass
        
        # 回退到当前日期
        if not derived_date:
            derived_date = datetime.datetime.now().strftime("%Y%m%d")
        
        # 重命名
        archive_name = f"{derived_date}_archive"
        archive_path = os.path.join(qdrive_drive, archive_name)
        
        if os.path.exists(archive_path):
            logger.warning(f"Archive folder {archive_path} already exists")
            return False
        
        # 等待其他进程释放句柄
        time.sleep(2)
        
        os.rename(data_path, archive_path)
        logger.info(f"✅ Qdrive data folder renamed: {data_path} → {archive_path}")
        
        return derived_date
        
    except Exception as e:
        logger.error(f"Error renaming Qdrive data folder: {e}")
        return False
```

#### 11.2 清理旧归档文件夹

```python
def _cleanup_qdrive_archives(self, qdrive_drive: str) -> Tuple[int, int]:
    """清理Qdrive根目录中的归档文件夹"""
    removed_count = 0
    error_count = 0
    
    try:
        for item in os.listdir(qdrive_drive):
            if 'archive' in item.lower():
                item_path = os.path.join(qdrive_drive, item)
                if os.path.isdir(item_path):
                    try:
                        shutil.rmtree(item_path)
                        removed_count += 1
                        logger.info(f"Removed archive folder: {item_path}")
                    except Exception as e:
                        error_count += 1
                        logger.warning(f"Failed to remove {item_path}: {e}")
    except Exception as e:
        logger.error(f"Error during Qdrive archive cleanup: {e}")
    
    return removed_count, error_count
```

### 12. 主程序流程

#### 12.1 交互式主程序

```python
def run(self):
    """运行交互式数据拷贝工具"""
    print("Interactive Data Copy Tool")
    print("="*60)
    
    try:
        # 1. 显示所有外部盘符
        external_drives = self.show_all_drives()
        if not external_drives:
            print("❌ No available external drives, program exiting")
            return
        
        # 2. 处理BitLocker解锁
        if not self.handle_bitlocker_unlock(external_drives):
            print("❌ BitLocker unlock failed, program exiting")
            return
        
        # 3. 自动识别所有盘符
        qdrive_drives, vector_drives, transfer_drives, backup_drives = self.detector.identify_data_drives(require_confirmation=True)
        
        # 存储识别的盘符
        self.qdrive_drives = qdrive_drives
        self.vector_drive = vector_drives[0] if vector_drives else None
        self.transfer_drive = transfer_drives[0] if transfer_drives else None
        self.backup_drive = backup_drives[0] if backup_drives else None
        
        # 4. 车型验证
        if self.vector_drive:
            detected_model = self._detect_vehicle_model_from_vector(self.vector_drive)
            if not self.config_manager.validate_vehicle_model(detected_model):
                print("❌ VEHICLE MODEL VALIDATION FAILED!")
                return
        
        # 5. 重复检测
        if self.vector_drive:
            has_duplicates, duplicates = self.detector.check_vector_duplicate_third_level(self.vector_drive)
            if has_duplicates:
                print("❌ Duplicate Vector date-time folders detected!")
                return
        
        # 6. 初始化日志
        self._initialize_logging()
        
        # 7. 创建拷贝计划
        self.copy_plan = self.create_copy_plan()
        
        # 8. 执行拷贝
        success = self.execute_copy_plan()
        
        # 9. 完整性验证
        if success:
            verification_passed = self.post_copy_verification()
            if not verification_passed:
                print("❌ Post-copy verification failed!")
                return False
        
        print("✅ Data copy operation completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during copy operation: {e}")
        return False
```

### 13. 错误处理与恢复

#### 13.1 异常处理策略

```python
def safe_execute_with_retry(func, max_retries: int = 3, delay: int = 5):
    """安全执行函数，支持重试"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Attempt {attempt + 1} failed: {e}, retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"All {max_retries} attempts failed: {e}")
                raise
```

#### 13.2 资源清理

```python
def cleanup_resources(self):
    """清理资源"""
    try:
        # 停止进度跟踪器
        if self.progress_tracker:
            self.progress_tracker.stop()
        
        # 关闭日志处理器
        for handler in copy_logger.handlers[:]:
            handler.close()
            copy_logger.removeHandler(handler)
        
        # 清理临时文件
        self._cleanup_temp_files()
        
    except Exception as e:
        logger.warning(f"Error during resource cleanup: {e}")
```

### 14. 性能优化

#### 14.1 并发控制

```python
def get_optimal_thread_count(self) -> int:
    """获取最优线程数"""
    config_threads = self.config_manager.get_max_concurrent_threads()
    cpu_count = os.cpu_count() or 4
    
    # 根据性能模式调整
    performance_mode = self.config_manager.get_performance_mode()
    
    if performance_mode == 'fast':
        return min(config_threads, cpu_count * 2)
    elif performance_mode == 'balanced':
        return min(config_threads, cpu_count)
    else:  # safe
        return min(config_threads, max(1, cpu_count // 2))
```

#### 14.2 内存管理

```python
def optimize_memory_usage(self):
    """优化内存使用"""
    # 根据性能模式调整缓冲区大小
    performance_mode = self.config_manager.get_performance_mode()
    
    if performance_mode == 'fast':
        # 使用大缓冲区
        buffer_size = self.config_manager.get_large_file_buffer_size()
    elif performance_mode == 'balanced':
        # 使用中等缓冲区
        buffer_size = self.config_manager.get_file_buffer_size()
    else:  # safe
        # 使用小缓冲区
        buffer_size = self.config_manager.get_file_buffer_size() // 2
    
    return buffer_size
```

### 15. 部署与使用

#### 15.1 环境要求

- Python 3.7+
- Windows 10/11 (主要支持)
- 足够的磁盘空间用于数据拷贝
- 管理员权限（用于BitLocker操作）

#### 15.2 安装步骤

```bash
# 1. 克隆项目
git clone <repository_url>
cd data-copy-tool

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置设置
cp copy_config.ini.example copy_config.ini
# 编辑配置文件

# 4. 运行程序
python data_copy_modules/interactive_main.py
```

#### 15.3 使用流程

1. **启动程序**：运行交互式主程序
2. **盘符识别**：程序自动识别所有外部盘符
3. **BitLocker解锁**：如有需要，输入密码解锁加密盘符
4. **车型验证**：验证Vector盘符中的车型是否匹配配置
5. **重复检测**：检查Vector数据是否与历史记录重复
6. **拷贝执行**：执行多线程数据拷贝
7. **进度监控**：实时显示拷贝进度
8. **完整性验证**：拷贝完成后进行四次比对验证
9. **日志记录**：所有操作记录到日志文件

### 16. 故障排除

#### 16.1 常见问题

1. **盘符识别失败**
   - 检查盘符标签是否正确
   - 确认data/logs文件夹存在
   - 检查文件权限

2. **拷贝速度慢**
   - 调整性能模式为fast
   - 增加并发线程数
   - 检查磁盘I/O性能

3. **验证失败**
   - 检查网络连接
   - 确认目标盘符空间充足
   - 调整验证容差

#### 16.2 日志分析

```python
def analyze_logs(log_directory: str):
    """分析日志文件"""
    datacopy_log = os.path.join(log_directory, "datacopy.txt")
    filelist_log = os.path.join(log_directory, "filelist.txt")
    
    # 分析拷贝日志
    with open(datacopy_log, 'r', encoding='utf-8') as f:
        content = f.read()
        
        # 查找错误信息
        errors = re.findall(r'ERROR.*', content)
        warnings = re.findall(r'WARNING.*', content)
        
        print(f"Errors: {len(errors)}")
        print(f"Warnings: {len(warnings)}")
        
        # 分析拷贝统计
        copy_stats = re.findall(r'copied.*files.*bytes', content)
        print(f"Copy operations: {len(copy_stats)}")
```

### 17. 扩展功能

#### 17.1 插件系统

```python
class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self.plugins = {}
    
    def register_plugin(self, name: str, plugin_class):
        """注册插件"""
        self.plugins[name] = plugin_class()
    
    def execute_plugin(self, name: str, *args, **kwargs):
        """执行插件"""
        if name in self.plugins:
            return self.plugins[name].execute(*args, **kwargs)
        return None
```

#### 17.2 自定义验证器

```python
class CustomValidator:
    """自定义验证器"""
    
    def validate_file_integrity(self, source: str, destination: str) -> bool:
        """验证文件完整性"""
        # 实现自定义验证逻辑
        pass
    
    def validate_directory_structure(self, path: str) -> bool:
        """验证目录结构"""
        # 实现自定义结构验证
        pass
```

### 18. 测试框架

#### 18.1 单元测试

```python
import unittest
from data_copy_modules.core.system_detector import CrossPlatformSystemDetector

class TestSystemDetector(unittest.TestCase):
    
    def setUp(self):
        self.detector = CrossPlatformSystemDetector()
    
    def test_qdrive_identification(self):
        """测试Qdrive识别"""
        # 模拟测试数据
        test_drives = ['C:\\', 'D:\\', 'E:\\']
        result = self.detector.identify_qdrive_drives(test_drives)
        self.assertIsInstance(result, list)
    
    def test_vector_identification(self):
        """测试Vector识别"""
        test_drives = ['F:\\', 'G:\\', 'H:\\']
        result = self.detector.identify_vector_drives(test_drives)
        self.assertIsInstance(result, list)
```

#### 18.2 集成测试

```python
class TestIntegration(unittest.TestCase):
    
    def test_full_copy_workflow(self):
        """测试完整拷贝工作流"""
        # 创建测试环境
        test_env = TestEnvironment()
        test_env.setup()
        
        try:
            # 执行完整流程
            tool = InteractiveDataCopyTool()
            result = tool.run()
            
            # 验证结果
            self.assertTrue(result)
            self.assertTrue(test_env.verify_copy_results())
            
        finally:
            test_env.cleanup()
```

### 19. 性能监控

#### 19.1 性能指标收集

```python
class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics = {
            'copy_speed': [],
            'memory_usage': [],
            'cpu_usage': [],
            'disk_io': []
        }
    
    def record_metric(self, metric_name: str, value: float):
        """记录性能指标"""
        if metric_name in self.metrics:
            self.metrics[metric_name].append({
                'value': value,
                'timestamp': time.time()
            })
    
    def get_average_speed(self) -> float:
        """获取平均拷贝速度"""
        if not self.metrics['copy_speed']:
            return 0.0
        
        total_speed = sum(m['value'] for m in self.metrics['copy_speed'])
        return total_speed / len(self.metrics['copy_speed'])
```

#### 19.2 性能报告生成

```python
def generate_performance_report(self) -> str:
    """生成性能报告"""
    report = []
    report.append("=" * 60)
    report.append("Performance Report")
    report.append("=" * 60)
    
    # 拷贝速度统计
    avg_speed = self.get_average_speed()
    report.append(f"Average Copy Speed: {avg_speed:.2f} MB/s")
    
    # 内存使用统计
    if self.metrics['memory_usage']:
        max_memory = max(m['value'] for m in self.metrics['memory_usage'])
        report.append(f"Peak Memory Usage: {max_memory:.2f} MB")
    
    # CPU使用统计
    if self.metrics['cpu_usage']:
        avg_cpu = sum(m['value'] for m in self.metrics['cpu_usage']) / len(self.metrics['cpu_usage'])
        report.append(f"Average CPU Usage: {avg_cpu:.2f}%")
    
    report.append("=" * 60)
    return "\n".join(report)
```

### 20. 安全考虑

#### 20.1 数据加密

```python
class DataEncryption:
    """数据加密类"""
    
    def __init__(self, key: str):
        self.key = key.encode()
    
    def encrypt_file(self, file_path: str) -> str:
        """加密文件"""
        # 实现文件加密逻辑
        pass
    
    def decrypt_file(self, encrypted_path: str) -> str:
        """解密文件"""
        # 实现文件解密逻辑
        pass
```

#### 20.2 访问控制

```python
class AccessControl:
    """访问控制类"""
    
    def __init__(self):
        self.permissions = {}
    
    def check_permission(self, user: str, resource: str) -> bool:
        """检查用户权限"""
        if user in self.permissions:
            return resource in self.permissions[user]
        return False
    
    def grant_permission(self, user: str, resource: str):
        """授予权限"""
        if user not in self.permissions:
            self.permissions[user] = set()
        self.permissions[user].add(resource)
```

## 总结

本数据拷贝工具是一个功能完整、设计精良的企业级应用程序，具有以下特点：

1. **模块化设计**：清晰的模块分离，便于维护和扩展
2. **配置驱动**：通过配置文件灵活控制各种参数
3. **智能识别**：自动识别不同类型的盘符
4. **严格验证**：车型验证和重复检测确保数据安全
5. **实时监控**：详细的进度跟踪和性能监控
6. **完整性保证**：四次比对验证确保拷贝完整性
7. **错误处理**：完善的异常处理和恢复机制
8. **日志记录**：详细的操作日志和文件结构记录
9. **性能优化**：多线程并发和智能缓冲区管理
10. **用户友好**：直观的交互界面和清晰的提示信息

该工具适用于需要处理大量车载数据的场景，能够确保数据拷贝的准确性、完整性和安全性。
