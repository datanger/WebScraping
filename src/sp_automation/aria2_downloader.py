"""
Aria2c 下载组件（断点续传 / 多连接 / 可注入请求头）

用途：
- 生成稳定的 aria2c 命令（支持断点续传与多连接），供外部执行
- 可选：直接在后台启动下载并输出日志

注意：
- 组件不负责抓取真实下载 URL/请求头；建议结合 CDP/拦截获得 url 与 headers
- 默认仅生成命令字符串，调用方按需执行
"""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Dict, List, Optional


class Aria2Options:
    """可配置的 aria2c 参数集合。"""

    def __init__(
        self,
        connections_per_server: int = 16,
        split: int = 16,
        piece_size: str = "1M",
        retry_wait_seconds: int = 5,
        max_tries: int = 0,
        timeout_seconds: int = 60,
        connect_timeout_seconds: int = 20,
        min_split_size: str = "1M",
        file_allocation: str = "none",
        auto_file_renaming: bool = False,
        overall_limit: Optional[str] = None,
        proxy: Optional[str] = None,
    ) -> None:
        self.connections_per_server = connections_per_server
        self.split = split
        self.piece_size = piece_size
        self.retry_wait_seconds = retry_wait_seconds
        self.max_tries = max_tries
        self.timeout_seconds = timeout_seconds
        self.connect_timeout_seconds = connect_timeout_seconds
        self.min_split_size = min_split_size
        self.file_allocation = file_allocation
        self.auto_file_renaming = auto_file_renaming
        self.overall_limit = overall_limit
        self.proxy = proxy


class Aria2Downloader:
    """生成并可运行 aria2c 下载命令的组件。"""

    @staticmethod
    def build_command(
        url: str,
        output_file: str,
        headers: Optional[Dict[str, str]] = None,
        options: Optional[Aria2Options] = None,
    ) -> List[str]:
        """构造 aria2c 命令（列表形式，适合 subprocess）。"""
        if options is None:
            options = Aria2Options()

        cmd: List[str] = [
            "aria2c",
            "-c",  # 断点续传
            f"-x{options.connections_per_server}",
            f"-s{options.split}",
            f"-k{options.piece_size}",
            "--file-allocation=none" if options.file_allocation == "none" else f"--file-allocation={options.file_allocation}",
            f"--retry-wait={options.retry_wait_seconds}",
            f"--max-tries={options.max_tries}",
            f"--timeout={options.timeout_seconds}",
            f"--connect-timeout={options.connect_timeout_seconds}",
            f"--min-split-size={options.min_split_size}",
            "--auto-file-renaming=false" if not options.auto_file_renaming else "--auto-file-renaming=true",
        ]

        if options.overall_limit:
            cmd.append(f"--max-overall-download-limit={options.overall_limit}")
        if options.proxy:
            cmd.append(f"--all-proxy={options.proxy}")

        # 注入请求头（如 Cookie/Authorization/UA/Referer）
        if headers:
            for k, v in headers.items():
                cmd.extend(["--header", f"{k}: {v}"])

        cmd.extend(["-o", output_file, url])
        return cmd

    @staticmethod
    def build_shell_command(
        url: str,
        output_file: str,
        headers: Optional[Dict[str, str]] = None,
        options: Optional[Aria2Options] = None,
    ) -> str:
        """构造可复制的 shell 命令字符串。"""
        parts = Aria2Downloader.build_command(url, output_file, headers, options)
        return " ".join(shlex.quote(p) for p in parts)

    @staticmethod
    def run_background(
        url: str,
        output_file: str,
        headers: Optional[Dict[str, str]] = None,
        options: Optional[Aria2Options] = None,
        log_file: Optional[str] = None,
        work_dir: Optional[str] = None,
    ) -> subprocess.Popen:
        """后台启动 aria2c 下载（非阻塞）。

        返回 subprocess.Popen 以便调用方管理进程；失败抛异常。
        """
        cmd = Aria2Downloader.build_command(url, output_file, headers, options)
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            with open(log_file, "ab", buffering=0) as lf:
                proc = subprocess.Popen(cmd, cwd=work_dir, stdout=lf, stderr=lf)
        else:
            proc = subprocess.Popen(cmd, cwd=work_dir)
        return proc


__all__ = ["Aria2Downloader", "Aria2Options"]


