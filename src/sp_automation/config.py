import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# 中文注释：加载 .env 文件，便于本地开发配置
# 对应计划：创建模块化项目结构与配置读取
load_dotenv()


@dataclass
class Settings:
    """集中式配置对象 - 所有配置都从.env文件读取"""

    # 登录/目标
    login_email: str = os.getenv("SP_LOGIN_EMAIL", "")
    login_password: str = os.getenv("SP_LOGIN_PASSWORD", "")
    target_url: str = os.getenv("SP_TARGET_URL", "")

    # 存储会话
    storage_state_file: str = os.getenv("SP_STORAGE_STATE", "storage/storage_state.json")

    # 浏览器参数
    headless: bool = os.getenv("SP_HEADLESS", "true").lower() == "true"
    slow_mo_ms: int = int(os.getenv("SP_SLOWMO_MS", "0"))
    proxy: Optional[str] = os.getenv("SP_PROXY", None)
    browser_type: str = os.getenv("SP_BROWSER_TYPE", "chromium")
    persistent_mode: bool = os.getenv("SP_PERSISTENT_MODE", "false").lower() == "true"
    user_data_dir: str = os.getenv("SP_USER_DATA_DIR", "storage/browser_profile")

    # 超时设置（ms）
    default_timeout_ms: int = int(os.getenv("SP_TIMEOUT_MS", "30000"))

    # MFA/OTP 相关
    mfa_provider: str = os.getenv("SP_MFA_PROVIDER", "manual")
    totp_secret: str = os.getenv("SP_TOTP_SECRET", "")

    imap_host: str = os.getenv("SP_IMAP_HOST", "")
    imap_user: str = os.getenv("SP_IMAP_USER", "")
    imap_password: str = os.getenv("SP_IMAP_PASSWORD", "")
    imap_folder: str = os.getenv("SP_IMAP_FOLDER", "INBOX")
    imap_ssl: bool = os.getenv("SP_IMAP_SSL", "true").lower() == "true"
    imap_search_subject_kw: str = os.getenv("SP_IMAP_SUBJECT_KW", "Microsoft 验证码")
    
    # 下载设置
    download_method: str = os.getenv("SP_DOWNLOAD_METHOD", "browser_default")
    download_path: str = os.getenv("SP_DOWNLOAD_PATH", "")
    
    # 批量下载设置
    batch_download_concurrency: int = int(os.getenv("BATCH_DOWNLOAD_CONCURRENCY", "2"))
    
    # 搜索路径设置
    search_path_separator: str = os.getenv("SP_SEARCH_PATH_SEPARATOR", "auto")
    use_windows_path_logic: bool = os.getenv("SP_USE_WINDOWS_PATH_LOGIC", "true").lower() == "true"
    search_timeout: int = int(os.getenv("SP_SEARCH_TIMEOUT", "30"))


settings = Settings()

__all__ = ["settings", "Settings"]