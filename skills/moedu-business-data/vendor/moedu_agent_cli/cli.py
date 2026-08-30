"""Command line entry point."""

import argparse
import getpass
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import quote

from . import __version__
from .client import ApiError, ApiResponse, Client
from .config import (
    ConfigError,
    audit_file,
    load_config,
    remove_saved_token,
    resolve_settings,
    save_config,
)
from .output import project_data, redact_pii, write_error, write_output
from .resources import RESOURCE_LIST, get_resource
from .web_auth import run_browser_login


AGENT_CLIENT_TYPE = 4


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="moedu-agent",
        description="Moedu 平台面向智能体的只读数据 CLI",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--base-url", help="平台地址；也可使用 MOEDU_BASE_URL")
    parser.add_argument("--agent-id", help="调用智能体标识；也可使用 MOEDU_AGENT_ID")
    parser.add_argument("--timeout", type=float, help="HTTP 超时秒数，默认 30")
    parser.add_argument("--insecure", action="store_true", help="禁用 HTTPS 证书校验")
    parser.add_argument("--no-local-audit", action="store_true", help="不写本机最小化审计日志")

    commands = parser.add_subparsers(dest="command", required=True)

    auth = commands.add_parser("auth", help="登录状态与本机凭据")
    auth_commands = auth.add_subparsers(dest="auth_command", required=True)
    login = auth_commands.add_parser("login", help="一次登录并保存智能体独立会话")
    login.add_argument("--username", required=True)
    login.add_argument("--password-stdin", action="store_true", help="从标准输入读取密码")
    login.add_argument(
        "--client-type",
        type=int,
        choices=(1, 2, 3, 4),
        default=AGENT_CLIENT_TYPE,
        help="登录会话类型，默认 4（智能体独立会话，不与 PC/H5 互相顶号）",
    )
    browser_login = auth_commands.add_parser(
        "browser-login",
        help="在本机浏览器完成一次授权，无需在命令行输入密码",
    )
    browser_login.add_argument("--username", help="预填账号，可省略")
    browser_login.add_argument(
        "--wait-seconds",
        type=int,
        default=300,
        help="等待浏览器授权的秒数，默认 300",
    )
    auth_commands.add_parser("status", help="查询当前登录账号")
    auth_commands.add_parser("logout", help="删除本机保存的 token")

    resources = commands.add_parser("resources", help="资源目录")
    resource_commands = resources.add_subparsers(dest="resource_command", required=True)
    resource_list = resource_commands.add_parser("list", help="列出资源")
    resource_domains = tuple(dict.fromkeys(resource.domain for resource in RESOURCE_LIST))
    resource_list.add_argument("--domain", choices=resource_domains)
    resource_list.add_argument("--format", choices=("json", "ndjson", "table"), default="json")
    describe = resource_commands.add_parser("describe", help="查看资源定义")
    describe.add_argument("resource")

    query = commands.add_parser("query", help="查询一个只读资源")
    query.add_argument("resource")
    query.add_argument("--filter", action="append", default=[], metavar="KEY=VALUE")
    query.add_argument("--body", help="附加 JSON 对象；与 filter 合并")
    query.add_argument("--page", type=int, default=1)
    query.add_argument("--limit", type=int, default=20)
    query.add_argument("--all", action="store_true", help="拉取全部分页，最多受 --max-pages 限制")
    query.add_argument("--max-pages", type=int, default=100)
    query.add_argument("--select", help="仅输出指定字段，逗号分隔，支持 a.b")
    query.add_argument("--format", choices=("json", "ndjson", "table"), default="json")
    query.add_argument("--include-sensitive", action="store_true", help="确认读取工资等受限资源")
    query.add_argument("--include-pii", action="store_true", help="不隐藏手机号、证件号等个人信息")

    detail = commands.add_parser("get", help="按主键读取资源详情")
    detail.add_argument("resource")
    detail.add_argument("id")
    detail.add_argument("--select", help="仅输出指定字段，逗号分隔，支持 a.b")
    detail.add_argument("--format", choices=("json", "ndjson", "table"), default="json")
    detail.add_argument("--include-sensitive", action="store_true")
    detail.add_argument("--include-pii", action="store_true")

    commands.add_parser("doctor", help="检查配置、鉴权和资源目录")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "resources":
            return _resources(args)
        if args.command == "auth":
            return _auth(args)
        settings = resolve_settings(args)
        client = Client(settings)
        if args.command == "query":
            return _query(args, client)
        if args.command == "get":
            return _get(args, client)
        if args.command == "doctor":
            return _doctor(args, client)
        raise ConfigError("unknown command")
    except (ConfigError, KeyError, ValueError) as exc:
        write_error({"ok": False, "error": {"type": "input_error", "message": str(exc)}})
        return 2
    except ApiError as exc:
        error = {
            "type": "api_error",
            "message": str(exc),
            "api_code": exc.api_code,
            "http_status": exc.http_status,
        }
        if exc.api_code == 302:
            error.update(
                {
                    "reauth_required": True,
                    "message": "保存的智能体会话已过期或被替换，请重新完成一次授权",
                    "hint": "运行 moedu-agent auth browser-login --username <账号>；浏览器授权一次后将复用独立会话",
                }
            )
        write_error(
            {
                "ok": False,
                "error": error,
                "request_id": exc.request_id,
            }
        )
        return 3


def _resources(args: Any) -> int:
    if args.resource_command == "list":
        rows = [resource.public_dict() for resource in RESOURCE_LIST]
        if args.domain:
            rows = [row for row in rows if row["domain"] == args.domain]
        write_output({"ok": True, "data": rows, "count": len(rows)}, args.format)
        return 0
    resource = get_resource(args.resource)
    write_output({"ok": True, "data": resource.public_dict()})
    return 0


def _auth(args: Any) -> int:
    if args.auth_command == "logout":
        removed = remove_saved_token()
        write_output({"ok": True, "data": {"saved_token_removed": removed}})
        return 0

    settings = resolve_settings(args)
    if args.auth_command == "browser-login":
        if args.wait_seconds < 30 or args.wait_seconds > 1800:
            raise ConfigError("wait-seconds must be between 30 and 1800")
        result = run_browser_login(
            settings,
            username=args.username,
            wait_seconds=args.wait_seconds,
            client_type=AGENT_CLIENT_TYPE,
        )
        write_output({"ok": True, "data": result})
        return 0
    if args.auth_command == "login":
        password = sys.stdin.readline().rstrip("\n") if args.password_stdin else getpass.getpass("Password: ")
        if not password:
            raise ConfigError("password cannot be empty")
        response = Client(settings).post(
            "login",
            {
                "username": args.username,
                "password": password,
                "type": args.client_type,
            },
            authenticated=False,
        )
        if not isinstance(response.data, dict) or not response.data.get("adminToken"):
            raise ApiError("login response did not contain adminToken", response.request_id)
        stored = load_config()
        stored.update(
            {
                "base_url": settings.api_base[: -len("/crm-api")],
                "token": response.data["adminToken"],
                "agent_id": settings.agent_id,
                "client_type": args.client_type,
                "username": args.username,
            }
        )
        save_config(stored)
        write_output(
            {
                "ok": True,
                "data": {
                    "authenticated": True,
                    "username": args.username,
                    "client_type": args.client_type,
                    "independent_session": args.client_type == AGENT_CLIENT_TYPE,
                    "config_saved": True,
                },
                "request_id": response.request_id,
            }
        )
        return 0

    response = Client(settings).post("adminUser/queryLoginUser", {})
    data = redact_pii(response.data, include_pii=False)
    write_output({"ok": True, "data": data, "request_id": response.request_id})
    return 0


def _query(args: Any, client: Client) -> int:
    resource = get_resource(args.resource)
    _confirm_resource_access(resource.sensitivity, args.include_sensitive)
    if args.page < 1 or args.limit < 1 or args.limit > 500:
        raise ValueError("page must be >= 1 and limit must be between 1 and 500")
    if args.max_pages < 1 or args.max_pages > 1000:
        raise ValueError("max-pages must be between 1 and 1000")

    body = dict(resource.default_body)
    body.update(_parse_filters(args.filter))
    body.update(_parse_body(args.body))
    if resource.paginated:
        body.update({"page": args.page, "limit": args.limit})

    if args.all and resource.paginated:
        data, page_meta, extra, responses = _fetch_all(client, resource.list_path, body, args.max_pages)
        response = responses[-1]
        duration_ms = sum(item.duration_ms for item in responses)
    else:
        response = client.post(resource.list_path, body)
        data, page_meta, extra = _normalize_data(response.data, resource.paginated)
        duration_ms = response.duration_ms

    data = redact_pii(data, include_pii=args.include_pii)
    data = project_data(data, _selected_fields(args.select))
    result: Dict[str, Any] = {
        "ok": True,
        "resource": resource.name,
        "request_id": response.request_id,
        "duration_ms": duration_ms,
        "data": data,
    }
    if page_meta is not None:
        result["page"] = page_meta
    if extra is not None:
        result["extra"] = redact_pii(extra, include_pii=args.include_pii)
    _append_audit(client, "query", resource.name, response, _row_count(data), "success")
    write_output(result, args.format)
    return 0


def _get(args: Any, client: Client) -> int:
    resource = get_resource(args.resource)
    _confirm_resource_access(resource.sensitivity, args.include_sensitive)
    if not resource.detail_path:
        raise ValueError("resource does not expose a detail route: {0}".format(resource.name))
    if resource.detail_body_key:
        path = resource.detail_path
        body = {resource.detail_body_key: _parse_scalar(args.id)}
    else:
        path = resource.detail_path.format(id=quote(str(args.id), safe=""))
        body = {}
    response = client.post(path, body)
    data = project_data(
        redact_pii(response.data, include_pii=args.include_pii),
        _selected_fields(args.select),
    )
    _append_audit(client, "get", resource.name, response, _row_count(data), "success")
    write_output(
        {
            "ok": True,
            "resource": resource.name,
            "request_id": response.request_id,
            "duration_ms": response.duration_ms,
            "data": data,
        },
        args.format,
    )
    return 0


def _doctor(args: Any, client: Client) -> int:
    response = client.post("adminUser/queryLoginUser", {})
    write_output(
        {
            "ok": True,
            "data": {
                "api_reachable": True,
                "authenticated": True,
                "api_base": client.settings.api_base,
                "agent_id": client.settings.agent_id,
                "resource_count": len(RESOURCE_LIST),
                "local_audit": client.settings.local_audit,
                "identity": redact_pii(response.data, include_pii=False),
            },
            "request_id": response.request_id,
            "duration_ms": response.duration_ms,
        }
    )
    return 0


def _fetch_all(
    client: Client,
    path: str,
    body: Dict[str, Any],
    max_pages: int,
) -> Tuple[List[Any], Dict[str, Any], Any, List[ApiResponse]]:
    start_page = int(body["page"])
    limit = int(body["limit"])
    rows: List[Any] = []
    responses: List[ApiResponse] = []
    extra = None
    total = None
    last_page = None
    for page in range(start_page, start_page + max_pages):
        current_body = dict(body)
        current_body["page"] = page
        response = client.post(path, current_body)
        responses.append(response)
        current_rows, meta, current_extra = _normalize_data(response.data, True)
        if not isinstance(current_rows, list):
            raise ApiError("paginated API did not return a list", response.request_id)
        rows.extend(current_rows)
        if current_extra is not None:
            extra = current_extra
        if meta:
            total = meta.get("total")
            last_page = meta.get("total_pages")
            if meta.get("last_page") is True or (last_page and page >= int(last_page)):
                break
        if len(current_rows) < limit:
            break
    page_meta = {
        "start_page": start_page,
        "page_size": limit,
        "pages_fetched": len(responses),
        "returned": len(rows),
        "total": total,
        "total_pages": last_page,
        "complete": bool(not last_page or responses and start_page + len(responses) - 1 >= int(last_page)),
    }
    return rows, page_meta, extra, responses


def _normalize_data(data: Any, paginated: bool) -> Tuple[Any, Optional[Dict[str, Any]], Any]:
    if paginated and isinstance(data, dict) and isinstance(data.get("list"), list):
        meta = {
            "number": data.get("pageNumber"),
            "size": data.get("pageSize"),
            "returned": len(data["list"]),
            "total": data.get("totalRow"),
            "total_pages": data.get("totalPage"),
            "first_page": data.get("firstPage"),
            "last_page": data.get("lastPage"),
        }
        return data["list"], meta, data.get("extraData")
    return data, None, None


def _parse_filters(values: Sequence[str]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("filter must use KEY=VALUE: {0}".format(value))
        key, raw = value.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("filter key cannot be empty")
        result[key] = _parse_scalar(raw)
    return result


def _parse_body(value: Optional[str]) -> Dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except ValueError as exc:
        raise ValueError("body must be valid JSON: {0}".format(exc))
    if not isinstance(parsed, dict):
        raise ValueError("body must be a JSON object")
    return parsed


def _parse_scalar(value: str) -> Any:
    try:
        return json.loads(value)
    except ValueError:
        return value


def _selected_fields(value: Optional[str]) -> List[str]:
    if not value:
        return []
    fields = [item.strip() for item in value.split(",") if item.strip()]
    if not fields:
        raise ValueError("select must contain at least one field")
    return fields


def _confirm_resource_access(sensitivity: str, include_sensitive: bool) -> None:
    if sensitivity == "restricted" and not include_sensitive:
        raise ValueError("restricted resource requires --include-sensitive and matching server permission")


def _row_count(data: Any) -> int:
    return len(data) if isinstance(data, list) else (0 if data is None else 1)


def _append_audit(
    client: Client,
    operation: str,
    resource: str,
    response: ApiResponse,
    row_count: int,
    status: str,
) -> None:
    if not client.settings.local_audit:
        return
    path = audit_file()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "resource": resource,
        "request_id": response.request_id,
        "agent_id": client.settings.agent_id,
        "status": status,
        "duration_ms": response.duration_ms,
        "row_count": row_count,
    }
    try:
        descriptor = os.open(str(path), os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            os.write(descriptor, (json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
        finally:
            os.close(descriptor)
        os.chmod(path, 0o600)
    except OSError as exc:
        raise ConfigError("cannot write local audit log {0}: {1}".format(path, exc))


if __name__ == "__main__":
    raise SystemExit(main())
