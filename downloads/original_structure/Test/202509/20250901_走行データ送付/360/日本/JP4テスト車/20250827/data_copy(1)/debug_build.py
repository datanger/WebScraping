#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Build Script for Data Copy Tool
Enhanced with detailed logging and error handling
"""

import os
import sys
import subprocess
import shutil
import time
from pathlib import Path

def check_environment():
    """Check the build environment"""
    print("🔍 Checking build environment...")
    
    # Check Python version
    print(f"Python version: {sys.version}")
    if sys.version_info < (3, 7):
        print("❌ Python 3.7+ is required")
        return False
    
    # Check if we're in the right directory
    if not os.path.exists("data_copy_modules"):
        print("❌ data_copy_modules directory not found!")
        print("Please run this script from the project root directory.")
        return False
    
    # Check main script
    main_script = "data_copy_modules/interactive_main.py"
    if not os.path.exists(main_script):
        print(f"❌ Main script not found: {main_script}")
        return False
    
    print("✅ Environment check passed")
    return True

def install_dependencies():
    """Install required dependencies with detailed output"""
    print("📦 Installing dependencies...")
    
    dependencies = [
        "pyinstaller>=5.13.0",
        "psutil>=5.9.0"
    ]
    
    for dep in dependencies:
        print(f"Installing {dep}...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", dep],
                check=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            print(f"✅ {dep} installed successfully")
        except subprocess.TimeoutExpired:
            print(f"❌ Timeout installing {dep}")
            return False
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {dep}: {e}")
            print(f"Error output: {e.stderr}")
            return False
    
    return True

def clean_build_dirs():
    """Clean previous build directories"""
    print("🧹 Cleaning previous builds...")
    
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"   Removed {dir_name}/")
            except Exception as e:
                print(f"   Warning: Could not remove {dir_name}/: {e}")
    
    # Clean .spec files
    for spec_file in Path('.').glob('*.spec'):
        try:
            spec_file.unlink()
            print(f"   Removed {spec_file}")
        except Exception as e:
            print(f"   Warning: Could not remove {spec_file}: {e}")

def test_pyinstaller():
    """Test PyInstaller with a simple command"""
    print("🧪 Testing PyInstaller...")
    
    try:
        result = subprocess.run(
            ["pyinstaller", "--version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        print(f"✅ PyInstaller version: {result.stdout.strip()}")
        return True
    except subprocess.TimeoutExpired:
        print("❌ PyInstaller command timed out")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ PyInstaller test failed: {e}")
        return False
    except FileNotFoundError:
        print("❌ PyInstaller not found in PATH")
        return False

def build_simple_version():
    """Build a simple version with minimal options"""
    print("🔨 Building simple version...")
    
    main_script = "data_copy_modules/interactive_main.py"
    
    # Simple command with minimal options
    cmd = [
        "pyinstaller",
        "--onefile",
        "--console",  # Always use console for debugging
        "--name=DataCopyTool_Simple",
        "--clean",
        main_script
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
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
                print("✅ Simple build completed successfully!")
                return True
            else:
                print(f"❌ Simple build failed with return code: {return_code}")
                return False
        except subprocess.TimeoutExpired:
            print("❌ Build timed out after 10 minutes")
            process.kill()
            return False
            
    except Exception as e:
        print(f"❌ Build failed with exception: {e}")
        return False

def build_with_data():
    """Build with data files included"""
    print("🔨 Building with data files...")
    
    main_script = "data_copy_modules/interactive_main.py"
    
    cmd = [
        "pyinstaller",
        "--onefile",
        "--console",
        "--name=DataCopyTool_WithData",
        "--add-data=data_copy_modules;data_copy_modules",
        "--hidden-import=psutil",
        "--hidden-import=logging",
        "--hidden-import=threading",
        "--hidden-import=datetime",
        "--hidden-import=os",
        "--hidden-import=time",
        "--clean",
        main_script
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
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
        
        try:
            return_code = process.wait(timeout=600)
            if return_code == 0:
                print("✅ Build with data completed successfully!")
                return True
            else:
                print(f"❌ Build with data failed with return code: {return_code}")
                return False
        except subprocess.TimeoutExpired:
            print("❌ Build with data timed out after 10 minutes")
            process.kill()
            return False
            
    except Exception as e:
        print(f"❌ Build with data failed with exception: {e}")
        return False

def check_build_output():
    """Check what was actually built"""
    print("📁 Checking build output...")
    
    if os.path.exists("dist"):
        print("dist/ directory exists")
        for item in os.listdir("dist"):
            item_path = os.path.join("dist", item)
            if os.path.isfile(item_path):
                size = os.path.getsize(item_path) / (1024*1024)  # MB
                print(f"   File: {item} ({size:.1f} MB)")
            else:
                print(f"   Directory: {item}")
    else:
        print("❌ dist/ directory does not exist")

def main():
    """Main debug build process"""
    print("🚀 Data Copy Tool - Debug Build Script")
    print("=" * 60)
    
    # Step 1: Check environment
    if not check_environment():
        return False
    
    # Step 2: Install dependencies
    if not install_dependencies():
        return False
    
    # Step 3: Test PyInstaller
    if not test_pyinstaller():
        return False
    
    # Step 4: Clean previous builds
    clean_build_dirs()
    
    # Step 5: Try simple build first
    print("\n" + "="*60)
    print("STEP 1: Simple Build (minimal options)")
    print("="*60)
    
    if build_simple_version():
        check_build_output()
        
        # Step 6: Try build with data
        print("\n" + "="*60)
        print("STEP 2: Build with Data Files")
        print("="*60)
        
        if build_with_data():
            check_build_output()
            print("\n🎉 All builds completed successfully!")
            return True
        else:
            print("\n⚠️ Simple build worked, but build with data failed")
            print("This suggests the issue is with data file inclusion")
            return False
    else:
        print("\n❌ Even simple build failed")
        print("This suggests a fundamental PyInstaller issue")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n💡 Troubleshooting tips:")
        print("1. Make sure you have enough disk space (at least 2GB)")
        print("2. Try running as administrator")
        print("3. Check if antivirus is blocking PyInstaller")
        print("4. Try running: pip install --upgrade pyinstaller")
        print("5. Check Windows Defender exclusions")
    
    input("\nPress Enter to exit...")
