# Data Copy Tool - 打包说明

## 概述
本目录包含了将数据拷贝工具打包成单个exe文件的所有必要脚本和配置文件。

## 文件说明

### 核心文件
- `requirements.txt` - Python依赖包列表
- `build_exe.py` - 基础打包脚本
- `advanced_build.py` - 高级打包脚本（推荐使用）
- `build.bat` - Windows批处理文件（一键打包）

### 生成的文件
- `dist/` - 打包后的可执行文件目录
- `build/` - 临时构建文件目录
- `*.spec` - PyInstaller配置文件

## 使用方法

### 方法1：使用批处理文件（推荐新手）
1. 双击运行 `build.bat`
2. 等待自动安装依赖和打包完成
3. 在 `dist/` 目录中找到生成的exe文件

### 方法2：使用Python脚本
```bash
# 基础打包
python build_exe.py

# 高级打包（推荐）
python advanced_build.py

# 只打包控制台版本
python advanced_build.py --version console

# 只打包窗口版本
python advanced_build.py --version windowed

# 只打包便携版本
python advanced_build.py --version portable

# 清理构建文件
python advanced_build.py --clean
```

## 生成的版本说明

### 1. DataCopyTool.exe（窗口版本）
- 无控制台窗口
- 适合普通用户使用
- 文件大小较小

### 2. DataCopyTool_Console.exe（控制台版本）
- 显示控制台窗口
- 适合调试和查看详细输出
- 可以看到实时进度信息

### 3. DataCopyTool_Portable（便携版本）
- 单目录结构
- 包含所有依赖文件
- 启动速度更快

## 系统要求

### 开发环境
- Python 3.7+
- Windows 10/11
- 至少2GB可用磁盘空间

### 运行环境
- Windows 10/11
- 无需安装Python
- 至少100MB可用磁盘空间

## 故障排除

### 常见问题

1. **PyInstaller未安装**
   ```
   解决方案：运行 pip install pyinstaller
   ```

2. **模块导入错误**
   ```
   解决方案：检查 data_copy_modules 目录是否存在
   ```

3. **打包文件过大**
   ```
   解决方案：使用 --exclude-module 排除不需要的模块
   ```

4. **运行时缺少DLL**
   ```
   解决方案：在目标机器上安装 Visual C++ Redistributable
   ```

### 调试模式
如果遇到问题，可以使用控制台版本进行调试：
```bash
python advanced_build.py --version console
```

## 自定义配置

### 添加图标
1. 将图标文件命名为 `icon.ico`
2. 放在项目根目录
3. 重新运行打包脚本

### 修改应用名称
编辑 `advanced_build.py` 中的 `name` 参数：
```python
spec_file = self.create_spec_file("YourAppName", console=True)
```

### 添加额外文件
在 `advanced_build.py` 的 `datas` 部分添加：
```python
datas=[
    ('data_copy_modules', 'data_copy_modules'),
    ('your_extra_files', 'your_extra_files'),  # 添加这行
],
```

## 性能优化

### 减小文件大小
1. 使用 `--exclude-module` 排除不需要的模块
2. 使用 `--onefile` 创建单文件版本
3. 启用 UPX 压缩（默认已启用）

### 提高启动速度
1. 使用 `--onedir` 创建目录版本
2. 预编译Python字节码
3. 减少隐藏导入的模块数量

## 分发说明

### 单文件分发
- 使用 `DataCopyTool.exe`（窗口版本）
- 文件大小约50-100MB
- 无需额外文件

### 目录分发
- 使用 `DataCopyTool_Portable` 目录
- 包含所有依赖文件
- 启动速度更快

### 安装包分发
- 使用生成的 `install.bat`
- 自动创建桌面快捷方式
- 安装到用户目录

## 更新日志

### v1.0.0
- 初始版本
- 支持基础打包功能
- 包含控制台和窗口版本

### v1.1.0
- 添加高级打包脚本
- 支持便携版本
- 添加安装脚本

## 技术支持

如果遇到打包问题，请检查：
1. Python版本是否为3.7+
2. 所有依赖是否正确安装
3. 项目目录结构是否完整
4. 是否有足够的磁盘空间

## 许可证

本打包脚本遵循与主项目相同的许可证。
