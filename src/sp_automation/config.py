import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# 中文注释：加载 .env 文件，便于本地开发配置
# 对应计划：创建模块化项目结构与配置读取
load_dotenv()


@dataclass
class Settings:
    """中文注释：集中式配置对象。"""

    # 登录/目标
    login_email: str = os.getenv("SP_LOGIN_EMAIL", "")
    login_password: str = os.getenv("SP_LOGIN_PASSWORD", "")  # 如需脚本输入密码
    target_url: str = os.getenv("SP_TARGET_URL", "https://scautoeng.sharepoint.com/sites/KOTEI-SCAE/Shared%20Documents/Forms/AllItems.aspx?id=%2Fsites%2FKOTEI%2DSCAE%2FShared%20Documents%2FGEN1%2E5%E4%B8%AD%E5%9B%BDFOT%2F%E3%83%87%E3%83%BC%E3%82%BF%E8%A7%A3%E6%9E%90%2F%E8%AA%8D%E8%AD%98%E7%B3%BB%2F%E8%B5%B0%E8%B7%AF%E8%AA%8D%E8%AD%98%2F%E3%82%B9%E3%82%AF%E3%83%AA%E3%83%97%E3%83%88%E6%A4%9C%E8%A8%8E%2FTest&viewid=8e19c37a%2Dacdb%2D4c40%2Da22e%2D92e27e7e3366&csf=1&web=1&e=NWcbWt&FolderCTID=0x01200090D0082931AED242A8680C59FF4AF68D")

    # 存储会话
    storage_state_file: str = os.getenv("SP_STORAGE_STATE", "storage/storage_state.json")

    # 浏览器参数
    headless: bool = os.getenv("SP_HEADLESS", "true").lower() == "true"
    slow_mo_ms: int = int(os.getenv("SP_SLOWMO_MS", "0"))
    proxy: Optional[str] = os.getenv("SP_PROXY", None)
    browser_type: str = os.getenv("SP_BROWSER_TYPE", "chromium")  # chromium|edge|firefox
    persistent_mode: bool = os.getenv("SP_PERSISTENT_MODE", "false").lower() == "true"
    user_data_dir: str = os.getenv("SP_USER_DATA_DIR", "storage/browser_profile")

    # 超时设置（ms）
    default_timeout_ms: int = int(os.getenv("SP_TIMEOUT_MS", "30000"))

    # MFA/OTP 相关
    mfa_provider: str = os.getenv("SP_MFA_PROVIDER", "manual")  # manual|totp|imap
    totp_secret: str = os.getenv("SP_TOTP_SECRET", "")  # TOTP 共享密钥（若使用 TOTP）

    imap_host: str = os.getenv("SP_IMAP_HOST", "")
    imap_user: str = os.getenv("SP_IMAP_USER", "")
    imap_password: str = os.getenv("SP_IMAP_PASSWORD", "")
    imap_folder: str = os.getenv("SP_IMAP_FOLDER", "INBOX")
    imap_ssl: bool = os.getenv("SP_IMAP_SSL", "true").lower() == "true"
    imap_search_subject_kw: str = os.getenv("SP_IMAP_SUBJECT_KW", "Microsoft 验证码")
    
    # 下载设置
    download_method: str = os.getenv("SP_DOWNLOAD_METHOD", "browser_default")  # browser_default|intercepted
    download_path: str = os.getenv("SP_DOWNLOAD_PATH", "")  # 空字符串表示使用浏览器默认路径
    
    # 批量下载设置
    batch_download_concurrency: int = int(os.getenv("BATCH_DOWNLOAD_CONCURRENCY", "2"))  # 并行下载数量


settings = Settings()

__all__ = ["settings", "Settings"]