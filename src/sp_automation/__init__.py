"""
中文说明：SharePoint 自动化（Playwright）包入口。
对应计划：创建模块化项目结构与配置读取。
包含模块：
- config：配置与环境变量读取
- browser：浏览器与上下文封装
- session：初始化并持久化登录会话
- sharepoint：SharePoint 导航与常用操作
- scraping：通用抓取函数
"""

__all__ = [
    "config",
    "browser",
    "session",
    "sharepoint",
    "scraping",
]
