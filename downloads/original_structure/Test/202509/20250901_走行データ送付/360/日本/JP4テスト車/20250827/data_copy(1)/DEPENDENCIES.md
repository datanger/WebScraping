# Data Copy Tool - 依赖说明

## 概述
本文档详细说明了数据拷贝工具的所有依赖项及其用途。

## 核心依赖

### 必需依赖 (requirements.txt)
```
psutil>=5.9.0          # 系统信息获取和磁盘管理
pyinstaller>=5.13.0    # 打包工具，用于创建exe文件
```

### 最小依赖 (requirements-minimal.txt)
```
psutil>=5.9.0          # 系统信息获取和磁盘管理
pyinstaller>=5.13.0    # 打包工具，用于创建exe文件
```

### 开发依赖 (requirements-dev.txt)
```
-r requirements.txt    # 包含所有生产依赖

# 测试框架
pytest>=7.0.0         # 单元测试框架
pytest-cov>=4.0.0     # 测试覆盖率

# 代码质量
black>=22.0.0         # 代码格式化
flake8>=5.0.0         # 代码检查
mypy>=1.0.0           # 类型检查

# 文档生成
sphinx>=5.0.0         # 文档生成工具
sphinx-rtd-theme>=1.0.0  # 文档主题

# 打包和分发
wheel>=0.37.0         # 打包工具
setuptools>=65.0.0    # 构建工具
twine>=4.0.0          # 包上传工具
```

## 依赖详细说明

### psutil
- **版本要求**: >=5.9.0
- **用途**: 
  - 获取磁盘使用情况
  - 获取驱动器信息
  - 系统资源监控
- **安装**: `pip install psutil>=5.9.0`

### pyinstaller
- **版本要求**: >=5.13.0
- **用途**:
  - 将Python脚本打包成exe文件
  - 创建单文件可执行程序
  - 处理依赖项打包
- **安装**: `pip install pyinstaller>=5.13.0`

## 内置模块 (无需安装)

以下模块是Python标准库的一部分，无需单独安装：

```
logging          # 日志记录
threading        # 多线程支持
datetime         # 日期时间处理
os               # 操作系统接口
time             # 时间相关功能
json             # JSON数据处理
re               # 正则表达式
shutil           # 高级文件操作
pathlib          # 路径处理
sys              # 系统特定参数
subprocess       # 子进程管理
glob             # 文件路径匹配
collections      # 集合数据类型
functools        # 函数工具
itertools        # 迭代器工具
```

## 安装方法

### 生产环境
```bash
# 安装核心依赖
pip install -r requirements.txt

# 或者安装最小依赖
pip install -r requirements-minimal.txt
```

### 开发环境
```bash
# 安装开发依赖（包含所有依赖）
pip install -r requirements-dev.txt
```

### 手动安装
```bash
# 核心依赖
pip install psutil>=5.9.0
pip install pyinstaller>=5.13.0

# 开发依赖（可选）
pip install pytest>=7.0.0
pip install black>=22.0.0
pip install flake8>=5.0.0
```

## 系统要求

### Python版本
- **最低要求**: Python 3.7+
- **推荐版本**: Python 3.9+
- **测试版本**: Python 3.10, 3.11

### 操作系统
- **Windows**: 10/11 (推荐)
- **Linux**: Ubuntu 18.04+, CentOS 7+
- **macOS**: 10.14+ (Mojave+)

### 硬件要求
- **内存**: 最少2GB RAM
- **磁盘空间**: 最少2GB可用空间
- **CPU**: 任何现代处理器

## 依赖冲突解决

### 常见问题

1. **psutil版本冲突**
   ```bash
   # 解决方案：升级到最新版本
   pip install --upgrade psutil
   ```

2. **pyinstaller版本过旧**
   ```bash
   # 解决方案：升级到推荐版本
   pip install --upgrade pyinstaller>=5.13.0
   ```

3. **Python版本不兼容**
   ```bash
   # 检查Python版本
   python --version
   
   # 如果版本过低，需要升级Python
   ```

### 虚拟环境使用

推荐使用虚拟环境来避免依赖冲突：

```bash
# 创建虚拟环境
python -m venv datacopy_env

# 激活虚拟环境
# Windows:
datacopy_env\Scripts\activate
# Linux/macOS:
source datacopy_env/bin/activate

# 安装依赖
pip install -r requirements.txt

# 使用完毕后退出
deactivate
```

## 版本兼容性

### psutil兼容性
- **5.9.0+**: 支持所有功能
- **5.8.x**: 基本功能支持
- **5.7.x及以下**: 可能缺少某些功能

### pyinstaller兼容性
- **5.13.0+**: 推荐版本，支持最新Python
- **5.10.x-5.12.x**: 基本支持
- **5.9.x及以下**: 可能不支持Python 3.11+

## 更新策略

### 定期更新
```bash
# 更新所有依赖到最新版本
pip install --upgrade -r requirements.txt

# 检查过时的包
pip list --outdated
```

### 安全更新
```bash
# 检查安全漏洞
pip audit

# 修复安全漏洞
pip install --upgrade package_name
```

## 故障排除

### 安装失败
1. 检查网络连接
2. 使用国内镜像源：
   ```bash
   pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
   ```
3. 升级pip：
   ```bash
   python -m pip install --upgrade pip
   ```

### 运行时错误
1. 检查依赖是否正确安装：
   ```bash
   pip list
   ```
2. 重新安装依赖：
   ```bash
   pip uninstall psutil pyinstaller
   pip install -r requirements.txt
   ```

## 许可证

所有依赖项都遵循其各自的许可证：
- **psutil**: BSD License
- **pyinstaller**: GPL License
- **其他开发依赖**: 各自许可证

## 联系支持

如果遇到依赖相关问题，请：
1. 检查本文档的故障排除部分
2. 查看各依赖项的官方文档
3. 提交issue到项目仓库
