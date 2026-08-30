"""Configuration and credential storage for the CLI."""

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlsplit, urlunsplit


DEFAULT_BASE_URL = "https://crm.moedu.com"
PRODUCTION_HOST = "crm.moedu.com"


class ConfigError(RuntimeError):
    pass


def config_dir() -> Path:
    root = os.environ.get("XDG_CONFIG_HOME")
    base = Path(root).expanduser() if root else Path.home() / ".config"
    return base / "moedu-agent"


def config_file() -> Path:
    override = os.environ.get("MOEDU_CONFIG_FILE")
    return Path(override).expanduser() if override else config_dir() / "config.json"


def audit_file() -> Path:
    override = os.environ.get("MOEDU_AUDIT_FILE")
    return Path(override).expanduser() if override else config_dir() / "audit.ndjson"


def load_config() -> Dict[str, Any]:
    path = config_file()
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConfigError("cannot read config {0}: {1}".format(path, exc))
    if not isinstance(value, dict):
        raise ConfigError("config must contain a JSON object: {0}".format(path))
    return value


def save_config(value: Dict[str, Any]) -> None:
    path = config_file()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix="config-", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def remove_saved_token() -> bool:
    value = load_config()
    existed = bool(value.pop("token", None))
    if existed:
        save_config(value)
    return existed


def normalize_api_base(value: str) -> str:
    base = secure_production_base_url(value).strip().rstrip("/")
    if not base:
        raise ConfigError("base URL cannot be empty")
    if base.endswith("/crm-api"):
        return base
    return base + "/crm-api"


def secure_production_base_url(value: str) -> str:
    """Upgrade only the canonical production host from HTTP to HTTPS.

    Test hosts and explicitly configured non-standard ports are left unchanged.
    """
    candidate = value.strip()
    parts = urlsplit(candidate)
    if (
        parts.scheme.lower() == "http"
        and parts.hostname == PRODUCTION_HOST
        and parts.port is None
    ):
        return urlunsplit(("https", parts.netloc, parts.path, parts.query, parts.fragment))
    return candidate


@dataclass(frozen=True)
class Settings:
    api_base: str
    token: Optional[str]
    agent_id: str
    timeout: float
    verify_tls: bool
    local_audit: bool


def resolve_settings(args: Any) -> Settings:
    stored = load_config()
    base_url = (
        getattr(args, "base_url", None)
        or os.environ.get("MOEDU_BASE_URL")
        or stored.get("base_url")
        or DEFAULT_BASE_URL
    )
    token = os.environ.get("MOEDU_TOKEN") or os.environ.get("MOEDU_ADMIN_TOKEN") or stored.get("token")
    agent_id = (
        getattr(args, "agent_id", None)
        or os.environ.get("MOEDU_AGENT_ID")
        or stored.get("agent_id")
        or "unspecified-agent"
    )
    timeout = float(getattr(args, "timeout", None) or os.environ.get("MOEDU_TIMEOUT") or 30)
    return Settings(
        api_base=normalize_api_base(str(base_url)),
        token=token,
        agent_id=str(agent_id),
        timeout=timeout,
        verify_tls=not bool(getattr(args, "insecure", False)),
        local_audit=not bool(getattr(args, "no_local_audit", False)),
    )
