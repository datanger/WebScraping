# 数据拷贝工具模块化项目

## 🏗️ 项目结构

```
data_copy_modules/
├── __init__.py                 # 主包初始化文件
├── main.py                     # 主程序入口
├── README.md                   # 项目说明文档
├── core/                       # 核心模块
│   ├── __init__.py
│   └── system_detector.py     # 系统检测器核心类
├── drivers/                    # 驱动器管理模块
│   ├── __init__.py
│   ├── drive_detector.py      # 驱动器检测器
│   └── bitlocker_manager.py   # BitLocker管理器
├── data_copy/                  # 数据拷贝模块
│   ├── __init__.py
│   ├── copy_manager.py        # 拷贝管理器
│   ├── vector_data_handler.py # Vector数据处理
│   └── qdrive_data_handler.py # Qdrive数据处理
├── utils/                      # 工具函数模块
│   ├── __init__.py
│   ├── file_utils.py          # 文件工具函数
│   └── progress_bar.py        # 进度条工具
└── logging_utils/              # 日志管理模块
    ├── __init__.py
    └── copy_logger.py         # 拷贝日志记录器
```

## 🎯 模块功能说明

### 1. **核心模块 (core)**
- **system_detector.py**: 主要的系统检测器类，整合所有功能模块
- 提供统一的接口来访问各个子模块的功能
- 管理整个数据拷贝流程

### 2. **驱动器管理模块 (drivers)**
- **drive_detector.py**: 负责检测、识别和分类系统中的所有驱动器
- **bitlocker_manager.py**: 专门处理Windows系统的BitLocker加密驱动器

### 3. **数据拷贝模块 (data_copy)**
- **vector_data_handler.py**: 处理Vector数据盘的日期检查和数据管理
- **qdrive_data_handler.py**: 处理Qdrive数据的车型提取和目录结构创建
- **copy_manager.py**: 管理所有拷贝操作的执行流程

### 4. **工具函数模块 (utils)**
- **file_utils.py**: 提供文件统计、大小格式化和目录树生成功能
- **progress_bar.py**: 提供进度条显示功能，支持tqdm和自定义实现

### 5. **日志管理模块 (logging_utils)**
- **copy_logger.py**: 专门管理拷贝操作的日志记录
- 生成时间戳命名的日志文件
- 分别记录拷贝操作和文件列表信息

## 🚀 使用方法

### 1. **直接运行主程序**
```bash
cd data_copy_modules
python main.py
```

### 2. **作为模块导入使用**
```python
from data_copy_modules import CrossPlatformSystemDetector

# 创建检测器实例
detector = CrossPlatformSystemDetector()

# 检测驱动器
drives = detector.detect_all_drives()

# 执行数据拷贝
success = detector.execute_data_copy_plan()
```

### 3. **单独使用某个模块**
```python
from data_copy_modules.drivers import DriveDetector
from data_copy_modules.utils import get_directory_stats

# 使用驱动器检测器
drive_detector = DriveDetector()
drives = drive_detector.detect_all_drives()

# 使用文件工具
stats = get_directory_stats("/path/to/directory")
```

## 🔧 模块依赖关系

```
main.py
└── core.system_detector
    ├── drivers.drive_detector
    ├── drivers.bitlocker_manager
    ├── data_copy.vector_data_handler
    ├── data_copy.qdrive_data_handler
    ├── utils.file_utils
    ├── utils.progress_bar
    └── logging_utils.copy_logger
```

## 📋 主要特性

### 1. **模块化设计**
- 每个功能模块独立，职责清晰
- 易于维护和扩展
- 支持单独测试和使用

### 2. **跨平台支持**
- 支持Windows、Linux、macOS
- 自动检测操作系统类型
- 适配不同系统的驱动器检测方式

### 3. **智能驱动器识别**
- 自动识别系统驱动器
- 智能分类源数据盘和目标盘
- 支持Qdrive和Vector数据盘识别

### 4. **完整的数据拷贝功能**
- 并行拷贝支持
- 进度条显示
- 文件完整性验证
- 详细的日志记录

### 5. **BitLocker支持**
- Windows系统BitLocker状态检查
- 自动解锁加密驱动器
- 支持恢复密钥解锁

## 🧪 测试

### 1. **模块测试**
```bash
# 测试驱动器检测模块
python -c "from data_copy_modules.drivers import DriveDetector; print('驱动器检测模块导入成功')"

# 测试工具函数模块
python -c "from data_copy_modules.utils import get_directory_stats; print('工具函数模块导入成功')"
```

### 2. **功能测试**
```bash
# 运行主程序测试
python main.py
```

## 📝 开发说明

### 1. **添加新功能**
- 在相应的模块中添加新的类或函数
- 更新模块的`__init__.py`文件
- 在主包`__init__.py`中导出新功能

### 2. **修改现有功能**
- 直接修改对应模块文件
- 保持接口兼容性
- 更新相关文档

### 3. **创建新模块**
- 创建新的目录和`__init__.py`文件
- 在主包`__init__.py`中导入新模块
- 更新项目结构文档

## 🔍 故障排除

### 1. **导入错误**
- 确保在正确的目录中运行
- 检查Python路径设置
- 验证模块文件完整性

### 2. **功能异常**
- 检查日志文件获取详细错误信息
- 验证系统权限设置
- 确认依赖库已正确安装

## 📚 相关文档

- `LOGGING_FEATURES_SUMMARY.md`: 日志功能详细说明
- `CODE_STRUCTURE_AND_FLOW.md`: 代码结构和流程说明
- `ENHANCED_FEATURES.md`: 增强功能说明

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 📄 许可证

本项目采用MIT许可证，详见LICENSE文件。 