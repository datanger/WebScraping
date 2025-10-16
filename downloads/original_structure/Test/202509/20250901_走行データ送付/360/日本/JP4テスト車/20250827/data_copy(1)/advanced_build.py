#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Build Script for Data Copy Tool
Supports multiple build configurations and options
"""

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path
from datetime import datetime

class DataCopyBuilder:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.main_script = "data_copy_modules/interactive_main.py"
        self.build_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def check_dependencies(self):
        """Check and install required dependencies"""
        print("🔍 Checking dependencies...")
        
        # Check Python version
        if sys.version_info < (3, 7):
            print("❌ Python 3.7+ is required")
            return False
        
        # Check PyInstaller
        try:
            import PyInstaller
            print(f"✅ PyInstaller: {PyInstaller.__version__}")
        except ImportError:
            print("📦 Installing PyInstaller...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller>=5.13.0"])
            except subprocess.CalledProcessError:
                print("❌ Failed to install PyInstaller")
                return False
        
        # Check psutil
        try:
            import psutil
            print(f"✅ psutil: {psutil.__version__}")
        except ImportError:
            print("📦 Installing psutil...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil>=5.9.0"])
            except subprocess.CalledProcessError:
                print("❌ Failed to install psutil")
                return False
        
        return True
    
    def clean_build(self):
        """Clean previous build artifacts"""
        print("🧹 Cleaning previous builds...")
        
        dirs_to_clean = ['build', 'dist', '__pycache__']
        for dir_name in dirs_to_clean:
            if os.path.exists(dir_name):
                shutil.rmtree(dir_name)
                print(f"   Removed {dir_name}/")
        
        # Clean .spec files
        for spec_file in self.project_root.glob('*.spec'):
            spec_file.unlink()
            print(f"   Removed {spec_file}")
    
    def create_spec_file(self, name, console=True, icon=None):
        """Create a PyInstaller spec file for advanced configuration"""
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{self.main_script}'],
    pathex=['{self.project_root}'],
    binaries=[],
    datas=[
        ('data_copy_modules', 'data_copy_modules'),
    ],
    hiddenimports=[
        'psutil',
        'logging',
        'threading',
        'datetime',
        'os',
        'time',
        'json',
        're',
        'shutil',
        'pathlib',
        'sys',
        'subprocess',
        'glob',
        'collections',
        'functools',
        'itertools',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console={str(console).lower()},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='{icon}' if icon and os.path.exists(icon) else None,
)
'''
        
        spec_file = f"{name}.spec"
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        return spec_file
    
    def build_with_spec(self, spec_file):
        """Build using a spec file"""
        print(f"🔨 Building with {spec_file}...")
        
        try:
            result = subprocess.run(
                ["pyinstaller", "--clean", spec_file],
                check=True,
                capture_output=True,
                text=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Build failed: {e}")
            print(f"Error: {e.stderr}")
            return False
    
    def build_console_version(self):
        """Build console version"""
        print("🔨 Building console version...")
        
        spec_file = self.create_spec_file("DataCopyTool_Console", console=True)
        success = self.build_with_spec(spec_file)
        
        if success:
            print("✅ Console version built successfully!")
        
        return success
    
    def build_windowed_version(self):
        """Build windowed version"""
        print("🔨 Building windowed version...")
        
        spec_file = self.create_spec_file("DataCopyTool", console=False)
        success = self.build_with_spec(spec_file)
        
        if success:
            print("✅ Windowed version built successfully!")
        
        return success
    
    def build_portable_version(self):
        """Build portable version (single directory)"""
        print("🔨 Building portable version...")
        
        cmd = [
            "pyinstaller",
            "--onedir",  # Single directory instead of single file
            "--console",
            "--name=DataCopyTool_Portable",
            "--add-data=data_copy_modules;data_copy_modules",
            "--hidden-import=psutil",
            "--hidden-import=logging",
            "--hidden-import=threading",
            "--hidden-import=datetime",
            "--hidden-import=os",
            "--hidden-import=time",
            "--hidden-import=json",
            "--hidden-import=re",
            "--hidden-import=shutil",
            "--hidden-import=pathlib",
            "--clean",
            self.main_script
        ]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("✅ Portable version built successfully!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Portable version build failed: {e}")
            return False
    
    def create_installer_script(self):
        """Create a simple installer script"""
        installer_content = '''@echo off
echo ========================================
echo Data Copy Tool - Installation
echo ========================================
echo.

REM Create installation directory
set INSTALL_DIR=%USERPROFILE%\\DataCopyTool
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM Copy executable
copy "DataCopyTool.exe" "%INSTALL_DIR%\\"
copy "DataCopyTool_Console.exe" "%INSTALL_DIR%\\"

REM Create desktop shortcut (optional)
echo Creating desktop shortcut...
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\\Desktop\\Data Copy Tool.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\\DataCopyTool.exe'; $Shortcut.Save()"

echo.
echo Installation completed!
echo Data Copy Tool has been installed to: %INSTALL_DIR%
echo Desktop shortcut created.
echo.
pause
'''
        
        with open("install.bat", "w", encoding="utf-8") as f:
            f.write(installer_content)
        
        print("📝 Created install.bat")
    
    def show_build_info(self):
        """Show build information"""
        print("\n" + "="*60)
        print("📦 BUILD INFORMATION")
        print("="*60)
        print(f"Build Time: {self.build_time}")
        print(f"Python Version: {sys.version}")
        print(f"Project Root: {self.project_root}")
        print(f"Main Script: {self.main_script}")
        
        if os.path.exists("dist"):
            print("\n📁 Generated Files:")
            for file in Path("dist").rglob("*"):
                if file.is_file():
                    size = file.stat().st_size / (1024*1024)  # MB
                    print(f"   {file.name} ({size:.1f} MB)")
    
    def build_all(self):
        """Build all versions"""
        print("🚀 Starting complete build process...")
        
        if not self.check_dependencies():
            return False
        
        self.clean_build()
        
        success = True
        
        # Build console version
        if not self.build_console_version():
            success = False
        
        # Build windowed version
        if not self.build_windowed_version():
            success = False
        
        # Build portable version
        if not self.build_portable_version():
            success = False
        
        # Create installer
        self.create_installer_script()
        
        # Show build info
        self.show_build_info()
        
        return success

def main():
    parser = argparse.ArgumentParser(description="Build Data Copy Tool")
    parser.add_argument("--version", choices=["console", "windowed", "portable", "all"], 
                       default="all", help="Build version to create")
    parser.add_argument("--clean", action="store_true", help="Clean build directories only")
    
    args = parser.parse_args()
    
    builder = DataCopyBuilder()
    
    if args.clean:
        builder.clean_build()
        print("✅ Clean completed")
        return
    
    if args.version == "all":
        success = builder.build_all()
    elif args.version == "console":
        success = builder.build_console_version()
    elif args.version == "windowed":
        success = builder.build_windowed_version()
    elif args.version == "portable":
        success = builder.build_portable_version()
    
    if success:
        print("\n🎉 Build completed successfully!")
        print("📁 Check the 'dist' directory for your executable files.")
    else:
        print("\n❌ Build failed. Please check the error messages above.")

if __name__ == "__main__":
    main()
