"""Operational events business tool (used to explain anomalies)."""

from __future__ import annotations

import datetime as dt

from app.database.connection import get_cursor
from app.tools.exceptions import ToolExecutionError
from app.tools.models import OperationalEvent, OperationalEventsResult
from app.tools.validation import validate_date_range, validate_severity

_OPERATIONAL_EVENTS_SQL = """
    SELECT
        event_id,
        order_id,
        event_type::text AS event_type,
        severity::text AS severity,
        event_date,
        description
    FROM operational_events
    WHERE event_date::date BETWEEN %(start_date)s AND %(end_date)s
      AND (%(severity)s::text IS NULL OR severity::text = %(severity)s)
    ORDER BY event_date
"""


def get_operational_events(
    start_date: dt.date | str, end_date: dt.date | str, severity: str | None = None
) -> OperationalEventsResult:
    """Operational events in a period, optionally filtered by severity."""
    start, end = validate_date_range(start_date, end_date)
    severity_filter = validate_severity(severity)

    try:
        with get_cursor() as cur:
            cur.execute(
                _OPERATIONAL_EVENTS_SQL,
                {"start_date": start, "end_date": end, "severity": severity_filter},
            )
            rows = cur.fetchall()
    except Exception as exc:  # pragma: no cover
        raise ToolExecutionError(f"get_operational_events failed: {exc}") from exc

    events = [OperationalEvent(**row) for row in rows]
    return OperationalEventsResult(
        start_date=start, end_date=end, severity_filter=severity_filter, events=events
    )
