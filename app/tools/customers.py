"""Customer performance business tool."""

from __future__ import annotations

import datetime as dt

from app.database.connection import get_cursor
from app.tools.exceptions import ToolExecutionError
from app.tools.models import CustomerPerformance, CustomerPerformanceItem
from app.tools.validation import validate_date_range, validate_top_n

_RECOGNIZED_STATUSES = ("paid", "shipped", "completed")

_CUSTOMER_PERFORMANCE_SQL = """
    SELECT
        c.customer_id,
        (c.first_name || ' ' || c.last_name) AS full_name,
        c.email,
        c.segment::text AS segment,
        SUM(oi.quantity * oi.unit_price)::float AS revenue,
        COUNT(DISTINCT o.order_id)::int AS order_count
    FROM order_items oi
    JOIN orders o ON o.order_id = oi.order_id
    JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.status::text = ANY(%(statuses)s)
      AND o.order_date::date BETWEEN %(start_date)s AND %(end_date)s
    GROUP BY c.customer_id, c.first_name, c.last_name, c.email, c.segment
    ORDER BY revenue DESC
    LIMIT %(top_n)s
"""


def get_customer_performance(
    start_date: dt.date | str, end_date: dt.date | str, top_n: int = 10
) -> CustomerPerformance:
    """Top customers by revenue for a period."""
    start, end = validate_date_range(start_date, end_date)
    n = validate_top_n(top_n)

    try:
        with get_cursor() as cur:
            cur.execute(
                _CUSTOMER_PERFORMANCE_SQL,
                {"statuses": list(_RECOGNIZED_STATUSES), "start_date": start, "end_date": end, "top_n": n},
            )
            rows = cur.fetchall()
    except Exception as exc:  # pragma: no cover
        raise ToolExecutionError(f"get_customer_performance failed: {exc}") from exc

    items = [CustomerPerformanceItem(**row) for row in rows]
    return CustomerPerformance(start_date=start, end_date=end, items=items)
