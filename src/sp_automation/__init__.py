"""
WebScraping 通用模块包入口
提供与业务无关的通用功能模块
包含模块：
- config：配置与环境变量读取
- browser：浏览器与上下文封装
- session：会话管理
- extractor：数据抽取
- element_detector：元素检测
- page_operations：页面操作
- safe_operations：安全操作（SharePoint文件保护）
- otp_providers：OTP认证
- sharepoint_scanner：SharePoint 文件结构扫描器核心
- file_downloader：文件下载器
- recursive_scanner：递归扫描器
- download_status_detector：下载状态检测器
 - cdp_download_monitor：浏览器原生下载器监控组件
 - aria2_downloader：aria2c 外部下载器集成
 - browser_aria2_bridge：浏览器→aria2 桥接组件
"""

__all__ = [
    "config",
    "browser", 
    "session",
    "extractor",
    "element_detector",
    "page_operations",
    "safe_operations",
    "otp_providers",
    "sharepoint_scanner",
    "file_downloader",
    "recursive_scanner",
    "download_status_detector",
    "cdp_download_monitor",
    "aria2_downloader",
    "browser_aria2_bridge",
    "login_status_detector",
]
