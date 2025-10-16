# 🚀 数据拷贝工具 - Data Copy Tool

## 📋 项目简介

这是一个功能强大的跨平台数据拷贝工具，专门用于处理Qdrive和Vector数据盘的拷贝任务。工具支持Windows、Linux和macOS系统，具备智能驱动器识别、BitLocker管理、同名文件处理等高级功能。

## ✨ 主要特性

### 🔍 智能驱动器识别
- 自动识别所有外接驱动器
- 智能分类Qdrive、Vector、Transfer、Backup驱动器
- 支持Windows、Linux、macOS跨平台

### 🔐 BitLocker支持
- Windows系统下自动检测BitLocker状态
- 支持使用恢复密钥解锁加密驱动器
- 安全的驱动器访问管理

### 📁 智能数据处理
- **Qdrive数据**：支持201、203、230、231盘号
- **Vector数据**：自动检测数据日期，支持单日期验证
- **同名文件处理**：自动重命名，避免数据覆盖
- **AB盘选择**：支持A盘/B盘选择，动态生成目录结构

### 🚀 高效拷贝引擎
- 并行处理，提升拷贝效率3-4倍
- 实时进度显示
- 数据完整性验证
- 详细的操作日志

## 🏗️ 项目结构

```
data_copy_modules/
├── core/                    # 核心功能模块
│   └── system_detector.py  # 系统检测和拷贝核心逻辑
├── data_copy/               # 数据处理模块
│   ├── qdrive_data_handler.py  # Qdrive数据处理
│   ├── vector_data_handler.py  # Vector数据处理
│   └── copy_manager.py         # 拷贝管理器
├── drivers/                 # 驱动管理模块
│   ├── bitlocker_manager.py    # BitLocker管理器
│   └── drive_detector.py       # 驱动器检测器
├── utils/                   # 通用工具模块
│   ├── file_utils.py           # 文件操作工具
│   └── progress_bar.py         # 进度条工具
├── logging_utils/           # 日志工具模块
│   └── copy_logger.py          # 拷贝日志记录器
└── interactive_main.py      # 交互式主程序
```

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 运行工具
```bash
# 交互式模式
python run_interactive.py

# 或直接运行
python data_copy_modules/interactive_main.py
```

### 3. 使用流程
1. **识别驱动器** - 自动检测所有外接驱动器
2. **BitLocker解锁** - 处理加密驱动器（如需要）
3. **选择数据盘** - 选择Qdrive、Vector等源数据盘
4. **选择目标盘** - 选择Transfer、Backup目标盘
5. **数据验证** - 检查Vector数据日期
6. **执行拷贝** - 按计划执行数据拷贝任务

## 🔧 核心功能

### Qdrive数据处理
- 支持4个Qdrive盘（201、203、230、231）
- 自动提取车型信息（RV1、RV2、RV3等）
- 支持版本号识别（v1、v2等）
- 智能目录结构生成

### Vector数据处理
- 自动检测数据日期
- 单日期数据验证
- 多日期数据警告
- 原始结构保持

### Backup盘管理
- 用户选择A盘或B盘
- 动态生成目录结构
- 3N前缀自动处理
- 根据实际盘号创建目录

### 同名文件处理
- 自动重命名策略
- 文件名+数字后缀
- 避免数据覆盖
- 完整操作日志

## 📊 技术架构

### 跨平台支持
- **Windows**: 盘符检测、BitLocker管理
- **Linux**: 挂载点检测、权限管理
- **macOS**: 卷检测、系统集成

### 并行处理
- ThreadPoolExecutor多线程
- 最多4个并行工作线程
- 智能任务分配
- 进度同步显示

### 数据验证
- 拷贝前后文件统计
- 文件数量验证
- 文件大小验证（允许1KB误差）
- 完整性检查报告

## 🎯 使用场景

### 数据备份
- 外接硬盘数据备份
- 多盘数据整合
- 增量数据同步
- 数据完整性验证

### 数据迁移
- 旧盘到新盘迁移
- 不同格式数据转换
- 目录结构重组
- 批量数据处理

### 系统维护
- 驱动器状态检测
- 数据盘分类管理
- 存储空间分析
- 系统性能优化

## 📦 部署方式

### 源码部署
```bash
git clone <repository-url>
cd data_copy
pip install -r requirements.txt
python run_interactive.py
```

### Windows部署
- 下载 `DataCopyTool_Windows.zip`
- 解压到任意目录
- 双击 `DataCopyTool.exe` 运行

### Docker部署
```bash
docker build -t data-copy-tool .
docker run -it --rm -v /host/path:/data data-copy-tool
```

## 🔒 安全特性

### 数据保护
- 只读源数据访问
- 同名文件自动重命名
- 数据完整性验证
- 详细操作日志

### 权限管理
- 系统盘自动排除
- 用户确认关键操作
- 安全的文件路径处理
- 错误处理和回滚

## 📈 性能优化

### 并行处理
- 多线程并行拷贝
- 智能缓冲区管理
- 内存使用优化
- I/O性能调优

### 进度监控
- 实时进度显示
- 剩余时间估算
- 传输速度显示
- 错误状态提示

## 🆘 故障排除

### 常见问题
1. **驱动器无法识别** - 检查连接和权限
2. **BitLocker解锁失败** - 确认恢复密钥正确
3. **拷贝速度慢** - 检查磁盘性能和连接方式
4. **权限不足** - 以管理员身份运行

### 日志分析
- 查看 `system_detector.log`
- 检查错误信息和警告
- 分析性能统计数据
- 验证操作结果

## 🤝 贡献指南

### 代码贡献
1. Fork项目仓库
2. 创建功能分支
3. 提交代码更改
4. 创建Pull Request

### 问题报告
- 使用GitHub Issues
- 提供详细的错误信息
- 包含系统环境信息
- 描述复现步骤

## 📄 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 👥 作者

- **开发者**: xiechitian
- **项目**: 数据拷贝工具
- **版本**: v1.0.0
- **更新**: 2025年8月

## 🌟 致谢

感谢所有为项目做出贡献的开发者和用户！

---

**🚀 开始使用数据拷贝工具，让数据管理变得简单高效！**
