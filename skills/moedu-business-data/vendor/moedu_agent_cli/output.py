"""Stable output, projection, and privacy helpers."""

import json
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence


_PII_KEYS = {
    "password",
    "admintoken",
    "accesstoken",
    "refreshtoken",
    "idcard",
    "identitycard",
    "bankcard",
    "bankaccount",
    "socialsecuritynumber",
    "providentfundaccount",
    "mobile",
    "phone",
    "telephone",
    "email",
    "address",
    "homeaddress",
    "contactaddress",
}


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def redact_pii(value: Any, include_pii: bool = False) -> Any:
    if include_pii:
        return value
    if isinstance(value, dict):
        return {
            key: ("[REDACTED]" if normalize_key(str(key)) in _PII_KEYS else redact_pii(item, False))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_pii(item, False) for item in value]
    return value


def project_data(data: Any, fields: Sequence[str]) -> Any:
    if not fields:
        return data
    if isinstance(data, list):
        return [_project_item(item, fields) for item in data]
    return _project_item(data, fields)


def _project_item(item: Any, fields: Sequence[str]) -> Any:
    if not isinstance(item, dict):
        return item
    return {field: _dot_get(item, field) for field in fields}


def _dot_get(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def write_output(value: Dict[str, Any], output_format: str = "json") -> None:
    if output_format == "json":
        json.dump(value, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return

    data = value.get("data")
    rows = data if isinstance(data, list) else [data]
    if output_format == "ndjson":
        for row in rows:
            json.dump(row, sys.stdout, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            sys.stdout.write("\n")
        return
    if output_format == "table":
        _write_table(rows)
        return
    raise ValueError("unsupported output format: {0}".format(output_format))


def write_error(value: Dict[str, Any]) -> None:
    json.dump(value, sys.stderr, ensure_ascii=False, sort_keys=True)
    sys.stderr.write("\n")


def _write_table(rows: Iterable[Any]) -> None:
    normalized = [row if isinstance(row, dict) else {"value": row} for row in rows]
    if not normalized:
        return
    columns: List[str] = []
    for row in normalized:
        for key in row:
            if key not in columns:
                columns.append(str(key))
        if len(columns) >= 20:
            break
    columns = columns[:20]
    rendered = [[_cell(row.get(column)) for column in columns] for row in normalized]
    widths = [len(column) for column in columns]
    for row in rendered:
        for index, cell in enumerate(row):
            widths[index] = min(60, max(widths[index], len(cell)))
    print("  ".join(column.ljust(widths[index]) for index, column in enumerate(columns)))
    print("  ".join("-" * widths[index] for index in range(len(columns))))
    for row in rendered:
        print("  ".join(row[index][: widths[index]].ljust(widths[index]) for index in range(len(columns))))


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value).replace("\n", " ")
