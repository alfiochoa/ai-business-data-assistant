"""Sales summary and period-comparison business tools."""

from __future__ import annotations

import datetime as dt

from app.database.connection import get_cursor
from app.tools.exceptions import ToolExecutionError
from app.tools.models import PeriodComparison, SalesSummary
from app.tools.validation import validate_date_range

_RECOGNIZED_STATUSES = ("paid", "shipped", "completed")

_SALES_SUMMARY_SQL = """
    SELECT
        COALESCE(SUM(oi.quantity * oi.unit_price), 0)::float AS total_revenue,
        COUNT(DISTINCT o.order_id)::int AS order_count
    FROM orders o
    LEFT JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.status = ANY(%(statuses)s)
      AND o.order_date::date BETWEEN %(start_date)s AND %(end_date)s
"""


def get_sales_summary(start_date: dt.date | str, end_date: dt.date | str) -> SalesSummary:
    """Total recognized revenue, order count, and average order value for a period."""
    start, end = validate_date_range(start_date, end_date)
    try:
        with get_cursor() as cur:
            cur.execute(
                _SALES_SUMMARY_SQL,
                {"statuses": list(_RECOGNIZED_STATUSES), "start_date": start, "end_date": end},
            )
            row = cur.fetchone()
    except Exception as exc:  # pragma: no cover - exercised via integration tests
        raise ToolExecutionError(f"get_sales_summary failed: {exc}") from exc

    total_revenue = row["total_revenue"] or 0.0
    order_count = row["order_count"] or 0
    avg_order_value = (total_revenue / order_count) if order_count else 0.0

    return SalesSummary(
        start_date=start,
        end_date=end,
        total_revenue=round(total_revenue, 2),
        order_count=order_count,
        avg_order_value=round(avg_order_value, 2),
    )


def compare_sales_periods(
    period_a_start: dt.date | str,
    period_a_end: dt.date | str,
    period_b_start: dt.date | str,
    period_b_end: dt.date | str,
) -> PeriodComparison:
    """Revenue/order-count for two periods, plus the delta between them."""
    period_a = get_sales_summary(period_a_start, period_a_end)
    period_b = get_sales_summary(period_b_start, period_b_end)

    revenue_delta = round(period_b.total_revenue - period_a.total_revenue, 2)
    revenue_delta_pct = (
        round((revenue_delta / period_a.total_revenue) * 100, 2)
        if period_a.total_revenue
        else None
    )
    order_count_delta = period_b.order_count - period_a.order_count

    return PeriodComparison(
        period_a=period_a,
        period_b=period_b,
        revenue_delta=revenue_delta,
        revenue_delta_pct=revenue_delta_pct,
        order_count_delta=order_count_delta,
    )
