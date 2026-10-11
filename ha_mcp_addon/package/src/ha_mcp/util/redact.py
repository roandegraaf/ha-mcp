"""Scrub secrets from log text before it is handed to a model."""

import re

_PATTERNS = (
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer [REDACTED]"),
    (re.compile(r"(?i)\b(eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)"), "[REDACTED_JWT]"),
    (re.compile(r"(?i)([a-z][a-z0-9+.-]*://)[^/\s:@]+:[^/\s@]+@"), r"\1[REDACTED]@"),
    # Quoted credentials (handles single or double quotes, passwords with spaces, etc.)
    (
        re.compile(
            r"""(?i)(?P<prefix>["\x27]?\b[a-z0-9_-]*(?:token|password|passwd|pwd|key|secret)\b["\x27]?\s*[:=]\s*)(?P<q>["\x27])(?P<val>[^\r\n]*?)(?P=q)"""
        ),
        r"\g<prefix>\g<q>[REDACTED]\g<q>",
    ),
    # Unquoted credentials
    (
        re.compile(
            r"""(?i)(?P<prefix>["\x27]?\b[a-z0-9_-]*(?:token|password|passwd|pwd|key|secret)\b["\x27]?\s*[:=]\s*)(?!["\x27])(?P<val>[^\s"'\r\n,&}]+)"""
        ),
        r"\g<prefix>[REDACTED]",
    ),
)

DEFAULT_MAX_CHARS = 20_000


def redact(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def tail(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[-max_chars:]
    newline = cut.find("\n")
    if 0 <= newline < 500:
        cut = cut[newline + 1 :]
    return f"[... truncated {len(text) - len(cut)} earlier characters ...]\n{cut}"
