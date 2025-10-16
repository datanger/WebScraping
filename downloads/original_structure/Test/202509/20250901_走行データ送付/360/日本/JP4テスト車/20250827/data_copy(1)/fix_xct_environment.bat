@echo off
echo ========================================
echo 修复xct环境中的驱动器识别问题
echo ========================================
echo.

echo 正在激活xct环境...
call conda activate xct

echo.
echo 正在安装pywin32模块...
pip install pywin32>=306

echo.
echo 正在验证安装...
python -c "import win32api; print('✅ pywin32安装成功')"

echo.
echo ========================================
echo 修复完成！
echo 现在可以重新运行数据拷贝工具了
echo ========================================
pause



