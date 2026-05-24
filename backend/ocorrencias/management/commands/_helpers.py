"""Shared parsers used by the load_* management commands."""

from __future__ import annotations

import datetime as dt
import math

from django.utils.timezone import is_naive, make_aware


def _is_nan(v: object) -> bool:
    return isinstance(v, float) and math.isnan(v)


def safe_str(raw: object, max_len: int | None = None) -> str:
    if raw is None or _is_nan(raw):
        return ""
    s = str(raw).strip()
    return s[:max_len] if max_len else s


def safe_int(raw: object) -> int | None:
    if raw is None or _is_nan(raw):
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return None


def safe_float(raw: object, decimal_sep: str = ".") -> float | None:
    """Parse float, optionally treating ``,`` as decimal separator (BR data)."""
    if raw is None or _is_nan(raw):
        return None
    s = str(raw).strip()
    if not s:
        return None
    if decimal_sep == ",":
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def safe_bool(raw: object) -> bool | None:
    if raw is None or _is_nan(raw):
        return None
    s = str(raw).strip().upper()
    if not s:
        return None
    if s in {"TRUE", "T", "1", "SIM", "S", "YES", "Y"}:
        return True
    if s in {"FALSE", "F", "0", "NÃO", "NAO", "N", "NO"}:
        return False
    return None


def safe_coord(raw: object, decimal_sep: str = ".") -> float | None:
    """Like :func:`safe_float` but rejects ``0.0`` (treated as missing)."""
    v = safe_float(raw, decimal_sep=decimal_sep)
    return None if v is None or v == 0.0 else v


def parse_datetime(raw: object, fmt: str) -> dt.datetime | None:
    if raw is None or _is_nan(raw):
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        parsed = dt.datetime.strptime(s, fmt)
    except ValueError:
        return None
    return make_aware(parsed) if is_naive(parsed) else parsed
