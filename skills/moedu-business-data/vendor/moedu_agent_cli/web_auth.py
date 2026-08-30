"""Loopback-only browser authorization for the Moedu agent CLI."""

import html
import secrets
import time
import webbrowser
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlsplit

from .client import ApiError, Client
from .config import ConfigError, Settings, load_config, save_config


MAX_FORM_BYTES = 16 * 1024


class BrowserAuthError(ConfigError):
    pass


def run_browser_login(
    settings: Settings,
    username: Optional[str],
    wait_seconds: int,
    client_type: int,
    open_browser: bool = True,
) -> Dict[str, Any]:
    """Open a local form and exchange credentials for an independent token.

    The listener is bound to loopback only. Passwords are kept in request-local
    memory and are never written to configuration or logs.
    """
    state = secrets.token_urlsafe(32)
    result: Dict[str, Any] = {}
    completed = {"value": False}
    expected_host = {"value": ""}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            parsed = urlsplit(self.path)
            query = parse_qs(parsed.query)
            if parsed.path != "/" or query.get("state") != [state]:
                self._send(404, "未找到授权页面")
                return
            self._send_form(username or "", "")

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
            if self.path != "/login" or self.headers.get("Host") != expected_host["value"]:
                self._send(404, "未找到授权页面")
                return
            try:
                length = int(self.headers.get("Content-Length") or "0")
            except ValueError:
                self._send(400, "请求格式不正确")
                return
            if length <= 0 or length > MAX_FORM_BYTES:
                self._send(400, "请求大小不正确")
                return
            values = parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
            form_state = (values.get("state") or [""])[0]
            form_username = (values.get("username") or [""])[0].strip()
            password = (values.get("password") or [""])[0]
            if not secrets.compare_digest(form_state, state):
                self._send(403, "授权页面已失效")
                return
            if not form_username or not password:
                self._send_form(form_username, "请输入账号和密码")
                return
            try:
                response = Client(replace(settings, token=None)).post(
                    "login",
                    {"username": form_username, "password": password, "type": client_type},
                    authenticated=False,
                )
                if not isinstance(response.data, dict) or not response.data.get("adminToken"):
                    raise BrowserAuthError("登录响应未返回有效会话")
                stored = load_config()
                stored.update(
                    {
                        "base_url": settings.api_base[: -len("/crm-api")],
                        "token": response.data["adminToken"],
                        "agent_id": settings.agent_id,
                        "client_type": client_type,
                        "username": form_username,
                    }
                )
                save_config(stored)
                result.update(
                    {
                        "authenticated": True,
                        "username": form_username,
                        "client_type": client_type,
                        "independent_session": True,
                        "config_saved": True,
                        "request_id": response.request_id,
                    }
                )
                completed["value"] = True
                self._send(200, "授权成功，可以关闭此页面。")
            except (ApiError, BrowserAuthError) as exc:
                self._send_form(form_username, str(exc))
            finally:
                password = ""

        def _send_form(self, form_username: str, error: str) -> None:
            error_html = (
                '<p class="error">{0}</p>'.format(html.escape(error)) if error else ""
            )
            body = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>摩度智能体授权</title><style>
body{margin:0;font:16px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f4f7fb;color:#172033}
main{max-width:420px;margin:10vh auto;padding:32px;background:white;border-radius:18px;box-shadow:0 14px 40px #183b6620}
h1{font-size:24px;margin:0 0 8px}.sub{color:#607089;margin:0 0 24px}.error{color:#b42318;background:#fef3f2;padding:10px;border-radius:8px}
label{display:block;margin:14px 0 6px;font-weight:600}input{box-sizing:border-box;width:100%;padding:12px;border:1px solid #cbd5e1;border-radius:9px;font-size:16px}
button{width:100%;margin-top:24px;padding:13px;border:0;border-radius:9px;background:#1769e0;color:white;font-size:16px;font-weight:700}
.note{font-size:13px;line-height:1.6;color:#718096;margin-top:18px}
</style></head><body><main><h1>摩度智能体一次授权</h1>
<p class="sub">授权后使用独立会话，不影响 PC 与 H5 登录。</p>__ERROR__
<form method="post" action="/login" autocomplete="off">
<input type="hidden" name="state" value="__STATE__">
<label for="username">账号</label><input id="username" name="username" value="__USERNAME__" required autofocus>
<label for="password">密码</label><input id="password" type="password" name="password" autocomplete="current-password" required>
<button type="submit">登录并授权</button></form>
<p class="note">页面只在本机 127.0.0.1 开放。密码仅发送到已配置的平台登录接口，不写入本机配置或日志。</p>
</main></body></html>"""
            body = (
                body.replace("__ERROR__", error_html)
                .replace("__STATE__", html.escape(state, quote=True))
                .replace("__USERNAME__", html.escape(form_username, quote=True))
            )
            self._send_html(200, body)

        def _send(self, status: int, message: str) -> None:
            self._send_html(
                status,
                "<!doctype html><meta charset=utf-8><title>摩度智能体授权</title>"
                "<p style='font:18px sans-serif;padding:40px'>{0}</p>".format(html.escape(message)),
            )

        def _send_html(self, status: int, body: str) -> None:
            payload = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
                "base-uri 'none'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(payload)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    expected_host["value"] = "127.0.0.1:{0}".format(server.server_port)
    login_url = "http://{0}/?state={1}".format(expected_host["value"], state)
    if open_browser and not webbrowser.open(login_url, new=2, autoraise=True):
        server.server_close()
        raise BrowserAuthError("无法自动打开浏览器，请检查系统默认浏览器设置")
    deadline = time.monotonic() + wait_seconds
    server.timeout = 1
    try:
        while not completed["value"] and time.monotonic() < deadline:
            server.handle_request()
    finally:
        server.server_close()
    if not completed["value"]:
        raise BrowserAuthError("浏览器授权等待超时，未保存任何新会话")
    return result
