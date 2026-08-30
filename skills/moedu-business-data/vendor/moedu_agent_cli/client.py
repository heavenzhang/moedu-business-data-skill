"""Small stdlib-only HTTP client for Wukong CRM APIs."""

import json
import ssl
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import Settings


class ApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        request_id: str,
        http_status: Optional[int] = None,
        api_code: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.request_id = request_id
        self.http_status = http_status
        self.api_code = api_code


@dataclass(frozen=True)
class ApiResponse:
    data: Any
    request_id: str
    duration_ms: int
    api_code: int
    message: str


class Client:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def post(
        self,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        authenticated: bool = True,
        request_id: Optional[str] = None,
    ) -> ApiResponse:
        current_request_id = request_id or str(uuid.uuid4())
        if authenticated and not self.settings.token:
            raise ApiError(
                "not authenticated; run 'moedu-agent auth login' or set MOEDU_TOKEN",
                current_request_id,
            )

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json;charset=UTF-8",
            "User-Agent": "moedu-agent-cli/0.1",
            "X-Moedu-Agent-Id": self.settings.agent_id,
            "X-Request-Id": current_request_id,
        }
        if authenticated and self.settings.token:
            headers["Admin-Token"] = self.settings.token

        payload = json.dumps(body or {}, ensure_ascii=False).encode("utf-8")
        request = Request(
            self.settings.api_base.rstrip("/") + "/" + path.lstrip("/"),
            data=payload,
            headers=headers,
            method="POST",
        )
        context = None
        if request.full_url.startswith("https://") and not self.settings.verify_tls:
            context = ssl._create_unverified_context()  # nosec: explicit --insecure only

        started = time.monotonic()
        try:
            with urlopen(request, timeout=self.settings.timeout, context=context) as response:
                raw = response.read().decode("utf-8")
                status = response.status
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            message = _error_message(raw) or "HTTP {0}".format(exc.code)
            raise ApiError(message, current_request_id, http_status=exc.code)
        except URLError as exc:
            raise ApiError("network error: {0}".format(exc.reason), current_request_id)

        duration_ms = int((time.monotonic() - started) * 1000)
        try:
            envelope = json.loads(raw)
        except ValueError:
            raise ApiError("server returned non-JSON response", current_request_id, http_status=status)
        if not isinstance(envelope, dict):
            raise ApiError("server returned an invalid JSON envelope", current_request_id, http_status=status)

        code = envelope.get("code")
        if code != 0:
            message = str(envelope.get("msg") or envelope.get("message") or "API request failed")
            raise ApiError(message, current_request_id, http_status=status, api_code=code)
        return ApiResponse(
            data=envelope.get("data"),
            request_id=current_request_id,
            duration_ms=duration_ms,
            api_code=int(code),
            message=str(envelope.get("msg") or envelope.get("message") or "success"),
        )


def _error_message(raw: str) -> Optional[str]:
    try:
        value = json.loads(raw)
    except ValueError:
        return raw[:300] if raw else None
    if isinstance(value, dict):
        return str(value.get("msg") or value.get("message") or "") or None
    return None
