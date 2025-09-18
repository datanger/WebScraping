"""
浏览器→aria2 桥接组件

作用：
- 在浏览器触发下载时，通过 CDP 捕获真实下载 URL（及尽可能的请求头），
  并用 aria2c 在后台接管下载，实现断点续传与多连接。

使用方式（示例）：
    status_manager = create_download_status_manager("downloads/download_state.json")
    bridge = BrowserToAria2Bridge(status_manager)
    await bridge.attach_to_page(page, output_dir="downloads", logs_dir="downloads/logs")
    # 之后照常在页面触发下载；桥接组件将自动启动 aria2c 并更新状态

限制：
- 仅 Chromium/Edge（CDP 支持）
- 部分场景无法完整获取请求头，将尽力从 Network 事件中关联
"""

from __future__ import annotations

import time
from pathlib import Path
import asyncio
from typing import Dict, Optional

from playwright.async_api import Page

from .aria2_downloader import Aria2Downloader, Aria2Options
from .download_status_detector import (
    DownloadStatus,
    DownloadStatusManager,
)


class BrowserToAria2Bridge:
    def __init__(self, status_manager: DownloadStatusManager, aria2_options: Optional[Aria2Options] = None) -> None:
        self.status_manager = status_manager
        self.aria2_options = aria2_options or Aria2Options()
        self._cdp = None
        self._last_request_headers_by_url: Dict[str, Dict[str, str]] = {}
        self._response_headers_by_url: Dict[str, Dict[str, str]] = {}
        self._user_agent: Optional[str] = None
        self._referer: Optional[str] = None

        # 记录 guid→task_id，便于后续回填
        self._guid_to_task: Dict[str, str] = {}
        # 记录任务监控：task_id -> asyncio.Task
        self._task_monitors: Dict[str, asyncio.Task] = {}
        # 记录任务总大小（从响应头推断 Content-Length）
        self._task_total_bytes: Dict[str, int] = {}
        # 记录需要被拦截中止的下载 URL 集合
        self._download_urls: set[str] = set()

        # 输出路径
        self._output_dir = Path("downloads")
        self._logs_dir = Path("downloads/logs")

    async def attach_to_page(self, page: Page, output_dir: Optional[str] = None, logs_dir: Optional[str] = None) -> None:
        if output_dir:
            self._output_dir = Path(output_dir)
        if logs_dir:
            self._logs_dir = Path(logs_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._logs_dir.mkdir(parents=True, exist_ok=True)

        context = page.context
        cdp = await context.new_cdp_session(page)
        self._cdp = cdp

        await cdp.send("Page.enable")
        await cdp.send("Network.enable")
        # 明确禁止浏览器接收下载，确保不会走浏览器下载器
        try:
            await cdp.send("Page.setDownloadBehavior", {"behavior": "deny"})
        except Exception:
            pass
        # Playwright 层兜底：如仍触发 download 事件，立即取消并用 aria2 接管
        try:
            def _on_download(dl):
                asyncio.create_task(self._handle_download_event(dl))
            page.on("download", _on_download)
        except Exception:
            pass
        # 启用请求拦截，用于中止浏览器自身的下载请求
        try:
            await cdp.send("Fetch.enable", {"patterns": [
                {"urlPattern": "*", "requestStage": "Request"},
                {"urlPattern": "*", "requestStage": "Response"}
            ]})
        except Exception:
            pass

        # 注入页面点击拦截：拦截含 href 的链接点击，转交 aria2
        try:
            async def _start_from_link_binding(source, href: str, suggested: str = ""):
                try:
                    await self.start_with_url(href, suggested or "downloaded_file")
                except Exception:
                    pass
            await page.expose_binding("aria2StartFromLink", _start_from_link_binding)
            await page.add_init_script(
                """
                (function(){
                  document.addEventListener('click', function(e){
                    try{
                      var a = e.target.closest('a[href]');
                      if(!a) return;
                      // Heuristic: links that likely trigger downloads
                      var href = a.getAttribute('href') || '';
                      var downloadAttr = a.getAttribute('download');
                      var text = (a.textContent||'').trim();
                      var isDownload = !!downloadAttr || /download/i.test(text) || /\.(zip|rar|7z|iso|exe|msi|pdf|docx?|xlsx?|pptx?)($|[?#])/i.test(href);
                      if(!isDownload) return;
                      e.preventDefault();
                      window.aria2StartFromLink(href, (a.getAttribute('download')||text||'downloaded_file'));
                    }catch(err){}
                  }, true);
                })();
                """
            )
        except Exception:
            pass

        # 尝试读取 UA（作为兜底）
        try:
            self._user_agent = await page.evaluate("navigator.userAgent")
            self._referer = page.url
        except Exception:
            pass

        async def on_request_will_be_sent(params):
            try:
                req = params.get("request", {})
                url = req.get("url")
                headers = req.get("headers", {})
                if isinstance(headers, dict) and url:
                    # 标准化 key 到首字母大写形式，aria2c 不要求，但更直观
                    norm = {str(k): str(v) for k, v in headers.items()}
                    self._last_request_headers_by_url[url] = norm
            except Exception:
                pass

        async def on_response_received(params):
            try:
                res = params.get("response", {})
                url = res.get("url")
                headers = res.get("headers", {})
                if isinstance(headers, dict) and url:
                    norm = {str(k): str(v) for k, v in headers.items()}
                    self._response_headers_by_url[url] = norm
                    # 命中附件响应，则将该 URL 纳入拦截名单
                    cd = None
                    for k, v in norm.items():
                        if k.lower() == "content-disposition":
                            cd = str(v)
                            break
                    if cd and "attachment" in cd.lower():
                        self._download_urls.add(str(url))
            except Exception:
                pass

        async def on_request_paused(params):
            """拦截并中止浏览器对下载 URL 的实际请求，确保由 aria2 接管。"""
            try:
                req = params.get("request", {})
                req_id = params.get("requestId")
                url = req.get("url")
                # 在响应阶段可读取响应头，判定下载
                if not url:
                    url = params.get("request", {}).get("url")
                stage = params.get("responseStatusCode")
                headers_list = params.get('responseHeaders') or []
                if headers_list and url:
                    try:
                        hdr = {h.get('name',''): h.get('value','') for h in headers_list if isinstance(h, dict)}
                        cd = None
                        for k,v in hdr.items():
                            if k.lower() == 'content-disposition':
                                cd = v
                                break
                        if cd and 'attachment' in cd.lower():
                            self._download_urls.add(str(url))
                    except Exception:
                        pass
                # 命中我们标记过的下载 URL，则中止该请求
                if url and url in self._download_urls and req_id:
                    try:
                        await self._cdp.send("Fetch.failRequest", {"requestId": req_id, "errorReason": "BlockedByClient"})
                    except Exception:
                        # 失败则尝试继续让其进行（不理想，但不致崩溃）
                        try:
                            await self._cdp.send("Fetch.continueRequest", {"requestId": req_id})
                        except Exception:
                            pass
                else:
                    # 非下载请求放行
                    if req_id:
                        try:
                            await self._cdp.send("Fetch.continueRequest", {"requestId": req_id})
                        except Exception:
                            pass
            except Exception:
                pass

        async def on_download_begin(params):
            guid = params.get("guid")
            url = params.get("url")
            suggested_raw = params.get("suggestedFilename") or "downloaded_file"
            suggested = self._sanitize_filename(suggested_raw)

            # 生成任务并标记为“外部下载器接管”
            file_info = {"name": suggested, "url": url, "method": "aria2c-bridge"}
            task = self.status_manager.create_task(file_info)
            self._guid_to_task[guid] = task.task_id
            if url:
                self._download_urls.add(str(url))
            self.status_manager.update_status(task.task_id, DownloadStatus.DOWNLOADING, suppress_log=True)

            # 组装 header
            headers = self._last_request_headers_by_url.get(url, {}).copy()
            # 兜底注入 UA/Referer（若未提供）
            if self._user_agent and "User-Agent" not in headers:
                headers["User-Agent"] = self._user_agent
            if self._referer and "Referer" not in headers:
                headers["Referer"] = self._referer

            # 启动 aria2c 后台下载
            output_path = self._output_dir / suggested
            log_path = self._logs_dir / f"{suggested}.log"
            try:
                proc = Aria2Downloader.run_background(
                    url=str(url),
                    output_file=str(output_path),
                    headers=headers,
                    options=self.aria2_options,
                    log_file=str(log_path),
                )
                print(f"➡️  已切换外部下载器 aria2c: {suggested}")
                # 记录总大小（如可用）
                total_bytes = None
                resp_h = self._response_headers_by_url.get(str(url), {})
                for k, v in resp_h.items():
                    if k.lower() == "content-length":
                        try:
                            total_bytes = int(v)
                        except Exception:
                            total_bytes = None
                        break
                if total_bytes is not None:
                    self._task_total_bytes[task.task_id] = total_bytes
                # 启动后台监控该任务（进程与文件稳定性）
                monitor = asyncio.create_task(
                    self._monitor_aria2_task(
                        task_id=task.task_id,
                        output_path=output_path,
                        proc=proc,
                    )
                )
                self._task_monitors[task.task_id] = monitor
                # 启动后健康检查：1s 内异常退出则失败
                async def _post_check():
                    try:
                        await asyncio.sleep(1)
                        if proc.poll() is not None and proc.returncode != 0:
                            self.status_manager.update_status(
                                task.task_id,
                                DownloadStatus.FAILED,
                                error_message=f"aria2 启动失败，退出码 {proc.returncode}",
                                suppress_log=False,
                            )
                    except Exception:
                        pass
                asyncio.create_task(_post_check())
            except Exception as e:
                self.status_manager.update_status(
                    task.task_id,
                    DownloadStatus.FAILED,
                    error_message=f"启动 aria2 失败: {e}",
                    suppress_log=False,
                )

        # 绑定事件
        cdp.on("Network.requestWillBeSent", on_request_will_be_sent)
        cdp.on("Network.responseReceived", on_response_received)
        cdp.on("Fetch.requestPaused", on_request_paused)
        cdp.on("Page.downloadWillBegin", on_download_begin)

    async def detach(self) -> None:
        # 仅释放引用；CDP 会话由浏览器上下文管理
        self._cdp = None

    async def _handle_download_event(self, dl) -> None:
        """当 Playwright download 事件触发时：提取 URL，取消浏览器下载，aria2 接管。"""
        try:
            url = None
            try:
                url = dl.url
            except Exception:
                url = None
            suggested = None
            try:
                suggested = await dl.suggested_filename()
            except Exception:
                pass
            suggested = self._sanitize_filename(suggested or "downloaded_file")

            # 取消浏览器侧下载
            try:
                await dl.cancel()
            except Exception:
                pass

            if not url:
                return

            # 直接调用统一入口启动 aria2
            await self.start_with_url(url, suggested)
        except Exception as e:
            # 安静失败，避免影响上层流程
            try:
                self.status_manager.update_status(
                    task.task_id,
                    DownloadStatus.FAILED,
                    error_message=f"download 事件接管失败: {e}",
                    suppress_log=False,
                )
            except Exception:
                pass

    async def start_with_url(self, url: str, suggested_name: str) -> None:
        """使用已知 URL 直接启动 aria2，并接入状态追踪。"""
        suggested = self._sanitize_filename(suggested_name or 'downloaded_file')
        # 生成任务
        file_info = {"name": suggested, "url": url, "method": "aria2c-bridge"}
        task = self.status_manager.create_task(file_info)
        self.status_manager.update_status(task.task_id, DownloadStatus.DOWNLOADING, suppress_log=True)

        # 准备头
        headers = self._last_request_headers_by_url.get(url, {}).copy()
        if self._user_agent and "User-Agent" not in headers:
            headers["User-Agent"] = self._user_agent
        if self._referer and "Referer" not in headers:
            headers["Referer"] = self._referer

        # 启动 aria2
        output_path = self._output_dir / suggested
        log_path = self._logs_dir / f"{suggested}.log"
        proc = Aria2Downloader.run_background(
            url=str(url),
            output_file=str(output_path),
            headers=headers,
            options=self.aria2_options,
            log_file=str(log_path),
        )

        # 监控与健康检查
        monitor = asyncio.create_task(
            self._monitor_aria2_task(task_id=task.task_id, output_path=output_path, proc=proc)
        )
        self._task_monitors[task.task_id] = monitor
        async def _post_check():
            await asyncio.sleep(1)
            if proc.poll() is not None and proc.returncode != 0:
                self.status_manager.update_status(
                    task.task_id,
                    DownloadStatus.FAILED,
                    error_message=f"aria2 启动失败，退出码 {proc.returncode}",
                    suppress_log=False,
                )
        asyncio.create_task(_post_check())

    async def _monitor_aria2_task(self, task_id: str, output_path: Path, proc) -> None:
        """监控 aria2c 进程与文件稳定性，回写 COMPLETED/FAILED。"""
        try:
            stable_checks_required = 3
            stable_interval = 0.5  # 秒
            no_progress_limit = 120  # 秒，无进展视为失败

            last_size = output_path.stat().st_size if output_path.exists() else 0
            last_change_time = asyncio.get_event_loop().time()
            stable_count = 0
            last_time = asyncio.get_event_loop().time()

            while True:
                # 进程是否已退出
                ret = proc.poll()

                # 文件大小检测
                current_size = output_path.stat().st_size if output_path.exists() else 0
                now = asyncio.get_event_loop().time()
                elapsed = max(now - last_time, 1e-6)
                speed = (current_size - last_size) / elapsed  # bytes/s
                last_time = now
                if current_size != last_size:
                    last_size = current_size
                    last_change_time = asyncio.get_event_loop().time()
                    stable_count = 0
                else:
                    stable_count += 1

                # 无进展超时判定
                if (asyncio.get_event_loop().time() - last_change_time) > no_progress_limit:
                    self.status_manager.update_status(
                        task_id,
                        DownloadStatus.FAILED,
                        error_message="aria2 下载无进展超时",
                        suppress_log=False,
                    )
                    return

                # 控制台单行进度
                try:
                    import sys as _sys
                    mb = current_size / (1024 * 1024)
                    mbps = speed / (1024 * 1024)
                    total = self._task_total_bytes.get(task_id)
                    if total and total > 0:
                        pct = current_size / total * 100.0
                        tot_mb = total / (1024 * 1024)
                        line = f"\r📥 {mb:.2f}MB / {tot_mb:.2f}MB  {pct:5.1f}%  {mbps:.2f} MB/s"
                    else:
                        line = f"\r📥 {mb:.2f}MB  ??.%  {mbps:.2f} MB/s"
                    _sys.stdout.write(line)
                    _sys.stdout.flush()
                except Exception:
                    pass

                # 进程退出且文件稳定若干次，视为完成/失败
                if ret is not None:
                    # 完成前换行
                    try:
                        import sys as _sys
                        _sys.stdout.write("\n")
                        _sys.stdout.flush()
                    except Exception:
                        pass
                    if ret == 0 and current_size > 0 and stable_count >= stable_checks_required:
                        self.status_manager.update_status(
                            task_id,
                            DownloadStatus.COMPLETED,
                            suppress_log=False,
                        )
                    else:
                        self.status_manager.update_status(
                            task_id,
                            DownloadStatus.FAILED,
                            error_message=f"aria2 退出代码 {ret}",
                            suppress_log=False,
                        )
                    return

                await asyncio.sleep(stable_interval)
        except Exception as e:
            self.status_manager.update_status(
                task_id,
                DownloadStatus.FAILED,
                error_message=f"监控异常: {e}",
                suppress_log=False,
            )

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """将建议文件名清理为安全文件名。"""
        # 去掉路径分隔与常见非法字符
        invalid = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        safe = name
        for ch in invalid:
            safe = safe.replace(ch, '_')
        # 避免空名
        safe = safe.strip() or 'downloaded_file'
        return safe


__all__ = ["BrowserToAria2Bridge"]


