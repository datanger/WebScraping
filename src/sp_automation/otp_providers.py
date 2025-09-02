import base64
import hmac
import hashlib
import struct
import time
import imaplib
import email
import re
from typing import Optional
from .config import settings

# 中文注释：OTP 提供器模块
# - TOTP：适用于 Microsoft Authenticator 兼容的 TOTP（需共享密钥）
# - IMAP：从邮箱收取“验证码”邮件并提取 6 位数字


def get_otp_from_provider() -> Optional[str]:
    """中文注释：根据配置选择 OTP 提供器。"""
    provider = settings.mfa_provider.lower()
    if provider == "totp" and settings.totp_secret:
        return generate_totp(settings.totp_secret)
    if provider == "imap" and settings.imap_host and settings.imap_user and settings.imap_password:
        return poll_imap_for_code(
            host=settings.imap_host,
            user=settings.imap_user,
            password=settings.imap_password,
            folder=settings.imap_folder,
            use_ssl=settings.imap_ssl,
            subject_kw=settings.imap_search_subject_kw,
        )
    # manual：返回 None，外层走人工输入
    return None


def generate_totp(secret: str, digits: int = 6, period: int = 30) -> str:
    """中文注释：标准 TOTP 生成（RFC 6238）。"""
    # 允许 Base32 / 原始密钥
    try:
        key = base64.b32decode(secret.replace(" ", "").upper())
    except Exception:
        key = secret.encode()
    counter = int(time.time()) // period
    msg = struct.pack("!Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    o = h[-1] & 0x0F
    code = (struct.unpack("!I", h[o:o+4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(code).zfill(digits)


def poll_imap_for_code(host: str, user: str, password: str, folder: str = "INBOX", use_ssl: bool = True, subject_kw: str = "验证码", timeout_sec: int = 120) -> Optional[str]:
    """中文注释：在超时时间内轮询 IMAP 邮箱，提取 6 位数字验证码。"""
    end = time.time() + timeout_sec
    mail = imaplib.IMAP4_SSL(host) if use_ssl else imaplib.IMAP4(host)
    mail.login(user, password)
    try:
        while time.time() < end:
            mail.select(folder)
            typ, data = mail.search(None, "ALL")
            if typ == "OK":
                ids = data[0].split()
                for mid in reversed(ids[-20:]):  # 仅检查最新的少量邮件
                    typ, msg_data = mail.fetch(mid, "(RFC822)")
                    if typ != "OK":
                        continue
                    msg = email.message_from_bytes(msg_data[0][1])
                    subject = str(email.header.make_header(email.header.decode_header(msg.get("Subject", ""))))
                    if subject_kw and subject_kw not in subject:
                        continue
                    body = _get_email_body(msg)
                    code = _extract_6digits(body) or _extract_6digits(subject)
                    if code:
                        return code
            time.sleep(5)
    finally:
        try:
            mail.logout()
        except Exception:
            pass
    return None


def _get_email_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                charset = part.get_content_charset() or "utf-8"
                try:
                    return part.get_payload(decode=True).decode(charset, errors="ignore")
                except Exception:
                    continue
    else:
        charset = msg.get_content_charset() or "utf-8"
        try:
            return msg.get_payload(decode=True).decode(charset, errors="ignore")
        except Exception:
            return ""
    return ""


def _extract_6digits(text: str) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"(?<!\d)(\d{6})(?!\d)", text)
    return m.group(1) if m else None
