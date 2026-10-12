"""Transaction-failure business tool."""

from __future__ import annotations

import datetime as dt

from app.database.connection import get_cursor
from app.tools.exceptions import ToolExecutionError
from app.tools.models import CustomerFailureItem, CustomerFailures, TransactionFailureSummary
from app.tools.validation import validate_date_range, validate_top_n

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


_CUSTOMER_FAILURES_SQL = """
    SELECT
        c.customer_id,
        (c.first_name || ' ' || c.last_name) AS full_name,
        c.email,
        COUNT(*) FILTER (WHERE t.status::text = ANY(%(failed_statuses)s))::int AS failed_count,
        COUNT(*)::int AS total_transactions,
        COALESCE(SUM(t.amount) FILTER (WHERE t.status::text = ANY(%(failed_statuses)s)), 0)::float AS failed_amount
    FROM transactions t
    JOIN orders o ON o.order_id = t.order_id
    JOIN customers c ON c.customer_id = o.customer_id
    WHERE t.transaction_date::date BETWEEN %(start_date)s AND %(end_date)s
    GROUP BY c.customer_id, c.first_name, c.last_name, c.email
    HAVING COUNT(*) FILTER (WHERE t.status::text = ANY(%(failed_statuses)s)) > 0
    ORDER BY failed_count DESC, failed_amount DESC
    LIMIT %(top_n)s
"""


def get_customer_failed_transactions(
    start_date: dt.date | str, end_date: dt.date | str, top_n: int = 10
) -> CustomerFailures:
    """Customers with the most failed/declined transactions in a period."""
    start, end = validate_date_range(start_date, end_date)
    n = validate_top_n(top_n)

    try:
        with get_cursor() as cur:
            cur.execute(
                _CUSTOMER_FAILURES_SQL,
                {"failed_statuses": list(_FAILED_STATUSES), "start_date": start, "end_date": end, "top_n": n},
            )
            rows = cur.fetchall()
    except Exception as exc:  # pragma: no cover
        raise ToolExecutionError(f"get_customer_failed_transactions failed: {exc}") from exc

    return CustomerFailures(
        start_date=start, end_date=end, items=[CustomerFailureItem(**row) for row in rows]
    )
