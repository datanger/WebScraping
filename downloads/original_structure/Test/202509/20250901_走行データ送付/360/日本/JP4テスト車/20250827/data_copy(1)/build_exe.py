#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Copy Tool - Build Script
Builds the data copy tool into a single executable file
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_pyinstaller():
    """Check if PyInstaller is installed"""
    try:
        import PyInstaller
        print(f"✅ PyInstaller found: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("❌ PyInstaller not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller>=5.13.0"])
            print("✅ PyInstaller installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install PyInstaller")
            return False

def clean_build_dirs():
    """Clean previous build directories"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"🧹 Cleaning {dir_name}...")
            shutil.rmtree(dir_name)
    
    # Clean .spec files
    for spec_file in Path('.').glob('*.spec'):
        print(f"🧹 Removing {spec_file}...")
        spec_file.unlink()

def build_executable():
    """Build the executable using PyInstaller"""
    print("🔨 Building executable...")
    
    # Main entry point
    main_script = "data_copy_modules/interactive_main.py"
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",                    # Create a single executable file
        "--windowed",                   # Hide console window (remove this if you want to see console)
        "--name=DataCopyTool",          # Name of the executable
        "--icon=icon.ico",              # Icon file (if exists)
        "--add-data=data_copy_modules;data_copy_modules",  # Include the data_copy_modules directory
        "--hidden-import=psutil",       # Ensure psutil is included
        "--hidden-import=logging",      # Ensure logging is included
        "--hidden-import=threading",    # Ensure threading is included
        "--hidden-import=datetime",     # Ensure datetime is included
        "--hidden-import=os",           # Ensure os is included
        "--hidden-import=time",         # Ensure time is included
        "--hidden-import=json",         # Ensure json is included
        "--hidden-import=re",           # Ensure re is included
        "--hidden-import=shutil",       # Ensure shutil is included
        "--hidden-import=pathlib",      # Ensure pathlib is included
        "--clean",                      # Clean cache and remove temp files
        main_script
    ]
    
    # Remove icon parameter if icon file doesn't exist
    if not os.path.exists("icon.ico"):
        cmd = [arg for arg in cmd if not arg.startswith("--icon")]
    
    try:
        print(f"Running command: {' '.join(cmd)}")
        print("This may take several minutes...")
        
        # Run with timeout and real-time output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Read output in real-time
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(f"PyInstaller: {output.strip()}")
        
        # Wait for completion with timeout
        try:
            return_code = process.wait(timeout=600)  # 10 minute timeout
            if return_code == 0:
                print("✅ Build completed successfully!")
                return True
            else:
                print(f"❌ Build failed with return code: {return_code}")
                return False
        except subprocess.TimeoutExpired:
            print("❌ Build timed out after 10 minutes")
            process.kill()
            return False
            
    except Exception as e:
        print(f"❌ Build failed with exception: {e}")
        return False

def create_console_version():
    """Create a console version (with visible console)"""
    print("🔨 Building console version...")
    
    main_script = "data_copy_modules/interactive_main.py"
    
    cmd = [
        "pyinstaller",
        "--onefile",                    # Create a single executable file
        "--console",                    # Show console window
        "--name=DataCopyTool_Console",  # Name of the console executable
        "--add-data=data_copy_modules;data_copy_modules",  # Include the data_copy_modules directory
        "--hidden-import=psutil",       # Ensure psutil is included
        "--hidden-import=logging",      # Ensure logging is included
        "--hidden-import=threading",    # Ensure threading is included
        "--hidden-import=datetime",     # Ensure datetime is included
        "--hidden-import=os",           # Ensure os is included
        "--hidden-import=time",         # Ensure time is included
        "--hidden-import=json",         # Ensure json is included
        "--hidden-import=re",           # Ensure re is included
        "--hidden-import=shutil",       # Ensure shutil is included
        "--hidden-import=pathlib",      # Ensure pathlib is included
        "--clean",                      # Clean cache and remove temp files
        main_script
    ]
    
    try:
        print(f"Running command: {' '.join(cmd)}")
        print("This may take several minutes...")
        
        # Run with timeout and real-time output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Read output in real-time
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(f"PyInstaller: {output.strip()}")
        
        # Wait for completion with timeout
        try:
            return_code = process.wait(timeout=600)  # 10 minute timeout
            if return_code == 0:
                print("✅ Console version built successfully!")
                return True
            else:
                print(f"❌ Console version build failed with return code: {return_code}")
                return False
        except subprocess.TimeoutExpired:
            print("❌ Console version build timed out after 10 minutes")
            process.kill()
            return False
            
    except Exception as e:
        print(f"❌ Console version build failed with exception: {e}")
        return False

def create_icon():
    """Create a simple icon file if it doesn't exist"""
    if not os.path.exists("icon.ico"):
        print("📝 Creating simple icon...")
        # Create a simple text-based icon (this is a placeholder)
        # In a real scenario, you would use a proper icon file
        print("ℹ️  No icon.ico found. Building without icon.")

def main():
    """Main build process"""
    print("🚀 Data Copy Tool - Build Script")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("data_copy_modules"):
        print("❌ Error: data_copy_modules directory not found!")
        print("Please run this script from the project root directory.")
        return False
    
    # Check PyInstaller
    if not check_pyinstaller():
        return False
    
    # Clean previous builds
    clean_build_dirs()
    
    # Create icon if needed
    create_icon()
    
    # Build executables
    success = True
    
    # Build windowed version
    if not build_executable():
        success = False
    
    # Build console version
    if not create_console_version():
        success = False
    
    if success:
        print("\n🎉 Build completed successfully!")
        print("📁 Executables created in 'dist' directory:")
        print("   - DataCopyTool.exe (Windowed version)")
        print("   - DataCopyTool_Console.exe (Console version)")
        print("\n💡 Usage:")
        print("   - Use DataCopyTool.exe for normal operation")
        print("   - Use DataCopyTool_Console.exe if you need to see console output")
    else:
        print("\n❌ Build failed. Please check the error messages above.")
    
    return success

if __name__ == "__main__":
    main()
