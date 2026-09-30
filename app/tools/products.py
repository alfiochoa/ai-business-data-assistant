"""Product performance business tool."""

from __future__ import annotations

import datetime as dt

from app.database.connection import get_cursor
from app.tools.exceptions import ToolExecutionError
from app.tools.models import ProductPerformance, ProductPerformanceItem
from app.tools.validation import validate_date_range, validate_top_n

_RECOGNIZED_STATUSES = ("paid", "shipped", "completed")

_PRODUCT_PERFORMANCE_SQL = """
    SELECT
        p.product_id,
        p.sku,
        p.name,
        p.category,
        SUM(oi.quantity * oi.unit_price)::float AS revenue,
        SUM(oi.quantity)::int AS quantity_sold
    FROM order_items oi
    JOIN orders o ON o.order_id = oi.order_id
    JOIN products p ON p.product_id = oi.product_id
    WHERE o.status = ANY(%(statuses)s)
      AND o.order_date::date BETWEEN %(start_date)s AND %(end_date)s
    GROUP BY p.product_id, p.sku, p.name, p.category
    ORDER BY revenue DESC
    LIMIT %(top_n)s
"""


def get_product_performance(
    start_date: dt.date | str, end_date: dt.date | str, top_n: int = 10
) -> ProductPerformance:
    """Top-selling products by revenue for a period."""
    start, end = validate_date_range(start_date, end_date)
    n = validate_top_n(top_n)

    try:
        with get_cursor() as cur:
            cur.execute(
                _PRODUCT_PERFORMANCE_SQL,
                {"statuses": list(_RECOGNIZED_STATUSES), "start_date": start, "end_date": end, "top_n": n},
            )
            rows = cur.fetchall()
    except Exception as exc:  # pragma: no cover
        raise ToolExecutionError(f"get_product_performance failed: {exc}") from exc

    items = [ProductPerformanceItem(**row) for row in rows]
    return ProductPerformance(start_date=start, end_date=end, items=items)
