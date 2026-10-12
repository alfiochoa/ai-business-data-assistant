"""Transaction-failure business tool."""

from __future__ import annotations

import datetime as dt

from app.database.connection import get_cursor
from app.tools.exceptions import ToolExecutionError
from app.tools.models import TransactionFailureSummary
from app.tools.validation import validate_date_range

_FAILED_STATUSES = ("failed", "declined")

_TRANSACTION_FAILURES_SQL = """
    SELECT
        COUNT(*)::int AS total_transactions,
        COUNT(*) FILTER (WHERE status::text = ANY(%(failed_statuses)s))::int AS failed_count
    FROM transactions
    WHERE transaction_date::date BETWEEN %(start_date)s AND %(end_date)s
"""


def get_transaction_failures(
    start_date: dt.date | str, end_date: dt.date | str
) -> TransactionFailureSummary:
    """Failed/declined transaction count and rate for a period."""
    start, end = validate_date_range(start_date, end_date)

    try:
        with get_cursor() as cur:
            cur.execute(
                _TRANSACTION_FAILURES_SQL,
                {"failed_statuses": list(_FAILED_STATUSES), "start_date": start, "end_date": end},
            )
            row = cur.fetchone()
    except Exception as exc:  # pragma: no cover
        raise ToolExecutionError(f"get_transaction_failures failed: {exc}") from exc

    total = row["total_transactions"] or 0
    failed = row["failed_count"] or 0
    failed_rate = round(failed / total, 4) if total else 0.0

    return TransactionFailureSummary(
        start_date=start,
        end_date=end,
        total_transactions=total,
        failed_count=failed,
        failed_rate=failed_rate,
    )
