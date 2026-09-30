"""Shared parameter validation for the business tool layer.

Every tool function must validate its parameters through these helpers
*before* touching the database. Validation happens against known, narrow
types (dates, small positive ints, a fixed enum of severities) — there is no
code path anywhere in this package that accepts a free-text value and drops
it into a SQL string, so there is nothing for a "SQL injection via natural
language" attempt to inject into.
"""

from __future__ import annotations

import datetime as dt

from app.tools.exceptions import ToolValidationError

MIN_DATE = dt.date(2000, 1, 1)
MAX_TOP_N = 100
ALLOWED_SEVERITIES = {"low", "medium", "high", "critical"}


def validate_date(value: dt.date | str, field_name: str) -> dt.date:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value)
        except ValueError as exc:
            raise ToolValidationError(
                f"{field_name!r} must be an ISO date (YYYY-MM-DD), got {value!r}."
            ) from exc
    raise ToolValidationError(
        f"{field_name!r} must be a date or ISO date string, got {type(value).__name__}."
    )


def validate_date_range(
    start_date: dt.date | str, end_date: dt.date | str
) -> tuple[dt.date, dt.date]:
    start = validate_date(start_date, "start_date")
    end = validate_date(end_date, "end_date")
    if start > end:
        raise ToolValidationError(
            f"start_date ({start}) must not be after end_date ({end})."
        )
    if start < MIN_DATE:
        raise ToolValidationError(f"start_date ({start}) is unreasonably far in the past.")
    today = dt.date.today()
    if end > today:
        raise ToolValidationError(
            f"end_date ({end}) is in the future; this system only has historical data."
        )
    return start, end


def validate_top_n(top_n: int, default: int = 10) -> int:
    if top_n is None:
        return default
    if isinstance(top_n, bool) or not isinstance(top_n, int):
        raise ToolValidationError(f"top_n must be an integer, got {top_n!r}.")
    if not (1 <= top_n <= MAX_TOP_N):
        raise ToolValidationError(f"top_n must be between 1 and {MAX_TOP_N}, got {top_n}.")
    return top_n


def validate_severity(severity: str | None) -> str | None:
    if severity is None:
        return None
    if severity not in ALLOWED_SEVERITIES:
        raise ToolValidationError(
            f"severity must be one of {sorted(ALLOWED_SEVERITIES)}, got {severity!r}."
        )
    return severity
