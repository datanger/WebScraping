# 🚀 Windows安装使用指南

## 📋 系统要求
- Windows 7/8/10/11 (64位)
- 无需安装Python
- 无需安装任何依赖包

## 🎯 使用方法

### 方法1：直接运行
1. 双击 `DataCopyTool.exe`
2. 按照提示操作

### 方法2：使用启动脚本
1. 双击 `启动数据拷贝工具.bat`
2. 工具会自动启动

### 方法3：命令行运行
1. 打开命令提示符
2. 切换到工具目录
3. 运行 `DataCopyTool.exe`

## 🔧 功能特性
- ✅ 自动识别所有外接驱动器
- ✅ 支持BitLocker加密驱动器解锁
- ✅ 智能分类Qdrive、Vector等数据盘
- ✅ 自动处理同名文件
- ✅ 支持A/B盘选择
- ✅ 完整的拷贝进度显示

## 📁 文件说明
- `DataCopyTool.exe` - 主程序文件
- `启动数据拷贝工具.bat` - Windows启动脚本
- `config.ini` - 配置文件
- `README.md` - 详细说明文档

## ⚠️ 注意事项
1. 首次运行可能需要Windows Defender允许
2. 确保有足够的磁盘空间
3. 建议以管理员身份运行（处理BitLocker时）

## 🆘 常见问题
Q: 运行时提示"Windows已保护你的电脑"
A: 点击"仍要运行"，这是正常的Windows安全提示

Q: 无法识别外接驱动器
A: 确保驱动器已正确连接并被Windows识别

Q: BitLocker解锁失败
A: 确保输入了正确的恢复密钥
