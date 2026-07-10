from __future__ import annotations

import re
from typing import Any

SECRET_PATTERNS = [
    ("provider_token", re.compile(r"sk-[A-Za-z0-9_-]{16,}")),
    ("provider_token", re.compile(r"(?:token|api[_-]?key)=[A-Za-z0-9._=-]{12,}", re.IGNORECASE)),
    ("provider_token", re.compile(r"Bearer\s+[A-Za-z0-9._=-]{12,}", re.IGNORECASE)),
]
SENSITIVE_KEYS = {"authorization", "api_key", "apikey", "access_token", "provider_token", "token"}
REDACTED = "[provider_token:redacted]"


def redact_secrets(text: str, provider_token: str | None = None) -> tuple[str, list[str]]:
    labels: list[str] = []
    redacted = text
    if provider_token and provider_token in redacted:
        labels.append("provider_token")
        redacted = redacted.replace(provider_token, REDACTED)
    for label, pattern in SECRET_PATTERNS:
        if pattern.search(redacted):
            labels.append(label)
            redacted = pattern.sub(f"[{label}:redacted]", redacted)
    return redacted, list(dict.fromkeys(labels))


def redact_value(value: Any, provider_token: str | None = None) -> tuple[Any, list[str]]:
    labels: list[str] = []
    if isinstance(value, str):
        return redact_secrets(value, provider_token)
    if isinstance(value, dict):
        result: dict[Any, Any] = {}
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in SENSITIVE_KEYS and item is not None and item != "":
                result[key] = REDACTED
                labels.append("provider_token")
                continue
            result[key], item_labels = redact_value(item, provider_token)
            labels.extend(item_labels)
        return result, list(dict.fromkeys(labels))
    if isinstance(value, list):
        result_list = []
        for item in value:
            redacted_item, item_labels = redact_value(item, provider_token)
            result_list.append(redacted_item)
            labels.extend(item_labels)
        return result_list, list(dict.fromkeys(labels))
    if isinstance(value, tuple):
        redacted_list, labels = redact_value(list(value), provider_token)
        return tuple(redacted_list), labels
    return value, labels
