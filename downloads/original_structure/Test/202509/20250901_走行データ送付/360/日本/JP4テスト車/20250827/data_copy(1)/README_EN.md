# Data Copy Tool User Manual (English)

## 📋 Tool Overview

The Data Copy Tool is an automated copying utility specifically designed for Qdrive and Vector data management, featuring multi-drive parallel copying, automatic drive identification, and comprehensive logging capabilities.

## 🚀 Key Features

### Automatic Drive Identification
- **Qdrive 201**: Automatically identifies drives containing `camera_fc*.mp4` files
- **Qdrive 203**: Automatically identifies drives containing `camera_rc*.mp4` files
- **Qdrive 230**: Automatically identifies drives containing `data_lidar_top` folders
- **Qdrive 231**: Automatically identifies drives containing `data_lidar_front` folders
- **Vector**: Automatically identifies drives containing `logs` folders
- **Transfer**: Automatically identifies drives with volume names starting with "Echo" but not ending with "backup"
- **Backup**: Automatically identifies drives with volume names starting with "Echo" and ending with "backup"

### High-Performance Copying
- **Multi-threaded Parallel Copying**: Automatically optimizes thread count based on CPU cores
- **Smart Buffer**: 32KB buffer size for enhanced copying efficiency
- **Real-time Progress Display**: Clear progress bars and file count indicators

### Comprehensive Logging
- **Copy Logs**: Detailed records of all copy operations
- **File Lists**: Complete file structure records of source drives
- **Timestamps**: Precise time records for all operations

## 🛠️ Installation Requirements

### System Requirements
- Windows 10/11
- Python 3.7+ (if running from source)

### Dependencies
```
psutil>=5.9.0
pywin32>=306
```

## 📦 Usage Methods

### Method 1: Run Executable
```bash
# Run the packaged exe file directly
DataCopyTool_Optimized.exe
```

### Method 2: Run from Source
```bash
# Install dependencies
pip install -r requirements.txt

# Run the program
python data_copy_modules/interactive_main.py
```

### Method 3: Rebuild Package
```bash
# Use optimized build script
build_optimized.bat

# Or build manually
pyinstaller -F --console --name=DataCopyTool_Optimized data_copy_modules/interactive_main.py
```

## 🔄 Usage Workflow

### 1. Launch Program
Upon startup, the program automatically:
- Detects all external drives
- Checks BitLocker status
- Automatically identifies Qdrive, Vector, Transfer, and Backup drives

### 2. Confirm Drive Identification
The program displays identification results including:
- Drive paths and volume names
- Folder structure analysis
- Identification reason explanations

Select `Y` to continue after confirming correct identification.

### 3. Check Vector Data Dates
The program checks data dates in the Vector drive to ensure data consistency.

### 4. Select Copy Plan
The program offers the following copy options:
- **Transfer Drive Copy**: Copy Qdrive and Vector data to Transfer drive
- **Backup Drive Copy**: Copy Qdrive and Vector data to Backup drive

### 5. Execute Copy
- Program automatically executes copying using high-performance mode
- Displays real-time progress bars and file counts
- All operations are logged to files

## 📁 Directory Structure

### Source Drive Structure
```
Qdrive Drive/
├── data/
│   └── 2qd_3NRV1_v1/
│       └── 2025_08_21-10_19/
│           ├── camera_fc_00.mp4
│           ├── camera_fl_00.mp4
│           └── ...

Vector Drive/
├── logs/
│   └── 3NRV1/
│       └── 20250818_193327/
│           ├── *.blf
│           ├── *.mf4
│           └── ...
```

### Target Drive Structure
```
Transfer Drive/
├── data/
│   ├── Qdrive_201/
│   │   └── 2025_08_21-10_19/
│   ├── Qdrive_203/
│   │   └── 2025_08_21-10_29/
│   └── ...
└── logs/
    └── Vector/
        └── 20250818_193327/

Backup Drive/
├── data/
│   ├── Qdrive_201/
│   ├── Qdrive_203/
│   └── ...
└── logs/
    └── Vector/
```

## 📊 Log Files

### Log Location
```
logs/
└── YYYYMMDD_HHMMSS/
    ├── datacopy.txt      # Copy operation logs
    └── filelist.txt      # File list logs
```

### Log Content
- **Copy Logs**: Operation time, source path, target path, file count, file size
- **File Lists**: Complete directory structure and file information
- **Error Information**: Detailed error descriptions and resolution suggestions

## ⚙️ Configuration Options

### High-Performance Mode Configuration
- **8+ Core CPU**: 6 parallel threads
- **4-7 Core CPU**: 4 parallel threads
- **<4 Core CPU**: 2 parallel threads
- **Buffer Size**: 32KB

### Progress Display
- Real-time progress bar display
- File count statistics
- Status icon indicators

## 🔧 Troubleshooting

### Common Issues

**1. Drive Not Recognized**
- Check if the drive is properly connected
- Verify the drive contains expected file structure
- Check drive permissions

**2. BitLocker Encrypted Drive**
- Program automatically detects BitLocker status
- Manual unlock required for encrypted drives

**3. Insufficient Permissions**
- Run the program as administrator
- Check write permissions on target drives

**4. Insufficient Space**
- Check available space on target drives
- Clean up unnecessary files

### Error Codes
- **Permission Error**: Check drive access permissions
- **Insufficient Space**: Free up space on target drive
- **File Locked**: Close programs that might be using the files

## 📞 Technical Support

If you encounter issues, please check:
1. Detailed error information in log files
2. System permission settings
3. Drive connection status
4. Target drive available space

## 📝 Update Log

### v1.0.0
- Initial version release
- Support for automatic drive identification
- Support for multi-threaded parallel copying
- Support for comprehensive logging

### v1.1.0
- Optimized progress display
- Removed mode selection, default high-performance mode
- Simplified user interface
- Improved error handling

## 📄 License

This project is licensed under the MIT License. See the LICENSE file for details.



