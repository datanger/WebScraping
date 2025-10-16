@echo off
chcp 65001 >nul
title PyInstaller最小化打包脚本 - 修复版

echo.
echo ========================================
echo      PyInstaller最小化打包脚本
echo           修复版 - 目录模式
echo ========================================
echo.

echo 🚀 开始最小化打包...
echo.

REM 清理构建目录
echo 🧹 清理构建目录...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__
for %%f in (*.spec) do del "%%f"

REM 检查PyInstaller是否安装
echo 🔍 检查PyInstaller...
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo ❌ PyInstaller未安装，正在安装...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo ❌ PyInstaller安装失败
        pause
        exit /b 1
    )
    echo ✅ PyInstaller安装完成
) else (
    echo ✅ PyInstaller已安装
)

REM 创建最小化spec文件
echo 📝 创建最小化spec文件...
(
echo # -*- mode: python ; coding: utf-8 -*-
echo.
echo block_cipher = None
echo.
echo # 分析阶段
echo a = Analysis(
echo     ['data_copy_modules/interactive_main.py'],
echo     pathex=[],
echo     binaries=[],
echo     datas=[
echo         ('config.ini', '.'^),
echo         ('data_copy_modules/README.md', 'data_copy_modules'^),
echo     ],
echo     hiddenimports=[
echo         'data_copy_modules.core.system_detector',
echo         'data_copy_modules.drivers.drive_detector',
echo         'data_copy_modules.drivers.bitlocker_manager',
echo         'data_copy_modules.data_copy.qdrive_data_handler',
echo         'data_copy_modules.data_copy.vector_data_handler',
echo         'data_copy_modules.data_copy.copy_manager',
echo         'data_copy_modules.utils.file_utils',
echo         'data_copy_modules.utils.progress_bar',
echo         'data_copy_modules.logging_utils.copy_logger',
echo     ],
echo     excludes=[
echo         'matplotlib', 'numpy', 'pandas', 'scipy', 'PIL', 'cv2',
echo         'tkinter', 'wx', 'PyQt5', 'PySide2', 'IPython', 'jupyter',
echo         'pytest', 'unittest', 'doctest', 'pdb', 'profile',
echo         'multiprocessing', 'concurrent.futures', 'asyncio',
echo         'sqlite3', 'xml', 'json', 'csv', 'pickle', 'shelve',
echo         'urllib', 'http', 'smtplib', 'poplib', 'imaplib',
echo         'ssl', 'cryptography', 'hashlib', 'hmac',
echo         'win32api', 'win32com', 'pywintypes', 'pythoncom',
echo         'comtypes', 'win32gui', 'win32con', 'win32process',
echo         'pywin32', 'py2exe', 'cx_Freeze', 'py2app',
echo     ],
echo     win_no_prefer_redirects=False,
echo     win_private_assemblies=False,
echo     cipher=block_cipher,
echo     noarchive=False,
echo ^)
echo.
echo # 构建阶段
echo pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher^)
echo.
echo # 可执行文件 - 使用目录模式避免DLL问题
echo exe = EXE(
echo     pyz,
echo     a.scripts,
echo     [],
echo     exclude_binaries=True,
echo     name='DataCopyTool_minimal',
echo     debug=False,
echo     bootloader_ignore_signals=False,
echo     strip=True,
echo     upx=True,
echo     upx_exclude=[],
echo     runtime_tmpdir=None,
echo     console=True,
echo     disable_windowed_traceback=False,
echo     argv_emulation=False,
echo     target_arch=None,
echo     codesign_identity=None,
echo     entitlements_file=None,
echo     icon=None,
echo     version_file=None,
echo ^)
echo.
echo # 收集所有文件到目录
echo coll = COLLECT(
echo     exe,
echo     a.binaries,
echo     a.zipfiles,
echo     a.datas,
echo     strip=True,
echo     upx=True,
echo     upx_exclude=[],
echo     name='DataCopyTool_minimal'
echo ^)
) > DataCopyTool_minimal.spec

echo ✅ 创建最小化spec文件完成

REM 使用PyInstaller构建
echo 🔨 开始构建exe文件...
pyinstaller --clean --noconfirm DataCopyTool_minimal.spec

if errorlevel 1 (
    echo ❌ PyInstaller构建失败
    pause
    exit /b 1
)

echo ✅ PyInstaller构建成功！

REM 创建启动脚本
echo 📝 创建启动脚本...
(
echo @echo off
echo chcp 65001 ^>nul
echo title 数据拷贝工具 - 最小化版本
echo echo.
echo echo ========================================
echo echo           数据拷贝工具
echo echo           最小化版本
echo echo ========================================
echo echo.
echo echo 正在启动程序...
echo echo.
echo.
echo DataCopyTool_minimal\DataCopyTool_minimal.exe
echo.
echo echo.
echo echo 程序执行完成，按任意键退出...
echo pause ^>nul
) > dist\启动数据拷贝工具.bat

echo ✅ 创建启动脚本完成

REM 显示结果
echo.
echo 🎉 打包完成！
echo ========================================
echo 📁 生成的文件:
echo    dist\DataCopyTool_minimal\DataCopyTool_minimal.exe
echo    dist\启动数据拷贝工具.bat
echo    dist\DataCopyTool_minimal\
echo.
echo 💡 使用说明:
echo    1. 运行 '启动数据拷贝工具.bat' 启动程序
echo    2. 或直接运行 'DataCopyTool_minimal\DataCopyTool_minimal.exe'
echo    3. 程序会自动创建logs目录存放日志
echo.

REM 显示文件大小
if exist dist\DataCopyTool_minimal\DataCopyTool_minimal.exe (
    for %%A in (dist\DataCopyTool_minimal\DataCopyTool_minimal.exe) do (
        set size=%%~zA
        set /a size_mb=!size!/1024/1024
        echo 📊 exe文件大小: !size_mb! MB
    )
)

echo.
echo 按任意键退出...
pause >nul
