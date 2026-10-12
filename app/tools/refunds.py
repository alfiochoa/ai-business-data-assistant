"""Refund business tool."""

from __future__ import annotations

import datetime as dt

from app.database.connection import get_cursor
from app.tools.exceptions import ToolExecutionError
from app.tools.models import RefundSummary
from app.tools.validation import validate_date_range

_REFUND_SQL = """
    SELECT
        COUNT(*)::int AS total_orders,
        COUNT(*) FILTER (WHERE o.status::text = 'refunded')::int AS refunded_orders,
        COALESCE((
            SELECT SUM(oi.quantity * oi.unit_price)
            FROM order_items oi
            JOIN orders r ON r.order_id = oi.order_id
            WHERE r.status::text = 'refunded'
              AND r.order_date::date BETWEEN %(start_date)s AND %(end_date)s
        ), 0)::float AS refunded_value
    FROM orders o
    WHERE o.order_date::date BETWEEN %(start_date)s AND %(end_date)s
"""


def get_refund_summary(start_date: dt.date | str, end_date: dt.date | str) -> RefundSummary:
    """Refunded order count, refund rate (share of orders) and refunded value for a period."""
    start, end = validate_date_range(start_date, end_date)

    try:
        with get_cursor() as cur:
            cur.execute(_REFUND_SQL, {"start_date": start, "end_date": end})
            row = cur.fetchone()
    except Exception as exc:  # pragma: no cover
        raise ToolExecutionError(f"get_refund_summary failed: {exc}") from exc

    total = row["total_orders"] or 0
    refunded = row["refunded_orders"] or 0
    return RefundSummary(
        start_date=start,
        end_date=end,
        total_orders=total,
        refunded_orders=refunded,
        refund_rate=round(refunded / total, 4) if total else 0.0,
        refunded_value=round(row["refunded_value"] or 0.0, 2),
    )
