from __future__ import annotations

import re

SECRET_PATTERNS = [
    ("provider_token", re.compile(r"demo-token-[A-Za-z0-9_-]{10,}")),
    ("provider_token", re.compile(r"token=[A-Za-z0-9._=-]{12,}", re.IGNORECASE)),
    ("provider_token", re.compile(r"Token\s+[A-Za-z0-9._-]{12,}", re.IGNORECASE)),
]


def redact_secrets(text: str) -> tuple[str, list[str]]:
    labels: list[str] = []
    redacted = text
    for label, pattern in SECRET_PATTERNS:
        if pattern.search(redacted):
            labels.append(label)
            redacted = pattern.sub(f"[{label}:redacted]", redacted)
    return redacted, labels
