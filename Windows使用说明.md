# Windows使用说明

## 📋 概述

本项目现已完全适配Windows环境，支持在Windows 10/11上运行SharePoint自动化下载功能。

## 🔧 环境要求

### 系统要求
- **操作系统：** Windows 10 或 Windows 11
- **Python版本：** 3.8 或更高版本
- **浏览器：** Microsoft Edge 或 Google Chrome

### 依赖安装

1. **安装Python依赖：**
   ```bash
   pip install -r requirements.txt
   ```

2. **安装Playwright浏览器：**
   ```bash
   playwright install
   ```

## 🚀 快速开始

### 1. 配置环境变量

创建 `.env` 文件（如果不存在）：
```bash
# SharePoint配置
SP_TARGET_URL=https://your-sharepoint-url
SP_LOGIN_EMAIL=your-email@company.com

# 下载配置
SP_DOWNLOAD_PATH=C:\Users\YourName\Downloads
# 或者使用相对路径
SP_DOWNLOAD_PATH=downloads

# 浏览器配置
SP_BROWSER_TYPE=chromium
SP_HEADLESS=false
```

### 2. 启动调试浏览器

```bash
python scripts/start_debug_browser.py
```

这将启动一个带调试端口的浏览器，您需要手动登录SharePoint。

### 3. 运行下载脚本

```bash
python scripts/scan_with_existing_browser_cdp.py
```

## 📁 目录结构

### Windows下的默认目录

```
项目根目录/
├── downloads/                    # 下载文件存储目录
│   ├── logs/                    # 日志文件
│   ├── reports/                 # 报告文件
│   └── original_structure/      # 解压后的文件结构
├── storage/                     # 浏览器配置和会话存储
│   └── browser_profile/         # 浏览器用户数据
└── scripts/                     # 脚本文件
```

### 用户数据目录

- **Windows：** `%USERPROFILE%\AppData\Local\debug_browser`
- **Linux/macOS：** `~/.config/debug_browser`

## 🔍 浏览器支持

### 支持的浏览器

1. **Microsoft Edge**
   - 默认路径：`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`
   - 备用路径：`C:\Program Files\Microsoft\Edge\Application\msedge.exe`

2. **Google Chrome**
   - 默认路径：`C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`
   - 备用路径：`C:\Program Files\Google\Chrome\Application\chrome.exe`

3. **Chromium**
   - 默认路径：`C:\Program Files (x86)\Chromium\Application\chrome.exe`
   - 备用路径：`C:\Program Files\Chromium\Application\chrome.exe`

### 浏览器检测优先级

1. 首先从系统PATH中查找浏览器
2. 然后尝试预定义的安装路径
3. 如果都找不到，会提示手动安装浏览器

## 📥 下载目录配置

### 默认下载路径检测顺序

1. **配置的下载目录**（如果设置了 `SP_DOWNLOAD_PATH`）
2. **当前运行目录下的downloads文件夹**
3. **系统默认下载目录**
   - `%USERPROFILE%\Downloads`
   - `%USERPROFILE%\下载`（中文系统）
4. **项目根目录下的downloads**

### 配置示例

```bash
# 使用绝对路径
SP_DOWNLOAD_PATH=C:\Users\YourName\Downloads

# 使用相对路径（相对于项目根目录）
SP_DOWNLOAD_PATH=downloads

# 使用自定义目录
SP_DOWNLOAD_PATH=./my_downloads
```

## 🧪 兼容性测试

运行兼容性测试脚本：
```bash
python scripts/test_windows_compatibility.py
```

这将测试：
- 平台检测
- 路径处理
- 浏览器检测
- 用户数据目录
- 下载路径检测
- 模块导入
- 文件操作

## 🔧 故障排除

### 常见问题

#### 1. 浏览器未找到
**错误：** `❌ 未找到浏览器可执行文件`

**解决方案：**
- 确保已安装Microsoft Edge或Google Chrome
- 检查浏览器是否安装在默认路径
- 手动指定浏览器路径

#### 2. 下载路径权限问题
**错误：** `PermissionError: [Errno 13] Permission denied`

**解决方案：**
- 以管理员身份运行命令提示符
- 检查下载目录的写入权限
- 更改下载目录到有权限的位置

#### 3. 模块导入失败
**错误：** `ModuleNotFoundError: No module named 'xxx'`

**解决方案：**
```bash
pip install -r requirements.txt
```

#### 4. Playwright浏览器未安装
**错误：** `Browser not found`

**解决方案：**
```bash
playwright install
```

### 调试模式

启用详细日志输出：
```bash
# 设置环境变量
set DEBUG=1

# 运行脚本
python scripts/scan_with_existing_browser_cdp.py
```

## 📊 性能优化

### Windows特定优化

1. **禁用Windows Defender实时保护**（临时）
   - 在下载大量文件时，可能会影响性能

2. **使用SSD存储**
   - 将下载目录设置在SSD上以提高I/O性能

3. **调整并发设置**
   ```bash
   # 在.env文件中设置
   BATCH_DOWNLOAD_CONCURRENCY=2
   ```

## 🔒 安全注意事项

### Windows安全设置

1. **用户账户控制（UAC）**
   - 可能需要管理员权限进行某些操作

2. **Windows Defender**
   - 可能会扫描下载的文件
   - 建议将下载目录添加到排除列表

3. **防火墙设置**
   - 确保允许Python和浏览器访问网络

## 📞 技术支持

如果遇到问题，请：

1. 运行兼容性测试脚本
2. 检查日志文件（`downloads/logs/`）
3. 查看错误信息和堆栈跟踪
4. 确认环境配置是否正确

## 📝 更新日志

### Windows适配版本 (v1.0)
- ✅ 修复硬编码路径问题
- ✅ 添加Windows浏览器路径支持
- ✅ 修复用户数据目录路径
- ✅ 改进下载目录检测
- ✅ 添加Windows兼容性测试脚本
- ✅ 完善错误处理和日志记录
