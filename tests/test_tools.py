"""Unit tests for the business tool layer's validation and SQL-binding logic.

No real database is used — app.database.connection.get_cursor is mocked out
in every test, so these verify (a) invalid input is rejected before any query
runs, and (b) valid input results in a parameterized query being executed
(never a string-formatted one).
"""

from __future__ import annotations

import datetime as dt
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from app.tools import customers, operations, products, sales, transactions
from app.tools.exceptions import ToolValidationError


def _fake_cursor(fetchone_result=None, fetchall_result=None):
    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone_result
    cursor.fetchall.return_value = fetchall_result or []

    @contextmanager
    def _get_cursor():
        yield cursor

    return cursor, _get_cursor


# --- get_sales_summary -------------------------------------------------


def test_get_sales_summary_rejects_inverted_range():
    with patch("app.tools.sales.get_cursor") as mock_get_cursor:
        with pytest.raises(ToolValidationError):
            sales.get_sales_summary("2024-05-01", "2024-01-01")
        mock_get_cursor.assert_not_called()


def test_get_sales_summary_rejects_future_end_date():
    future = (dt.date.today() + dt.timedelta(days=30)).isoformat()
    with patch("app.tools.sales.get_cursor") as mock_get_cursor:
        with pytest.raises(ToolValidationError):
            sales.get_sales_summary("2024-01-01", future)
        mock_get_cursor.assert_not_called()


def test_get_sales_summary_rejects_malformed_date():
    with patch("app.tools.sales.get_cursor") as mock_get_cursor:
        with pytest.raises(ToolValidationError):
            sales.get_sales_summary("2024-01-01; DROP TABLE orders;", "2024-02-01")
        mock_get_cursor.assert_not_called()


def test_get_sales_summary_executes_parameterized_query_and_computes_avg():
    cursor, get_cursor_cm = _fake_cursor(fetchone_result={"total_revenue": 1000.0, "order_count": 4})
    with patch("app.tools.sales.get_cursor", get_cursor_cm):
        result = sales.get_sales_summary("2024-01-01", "2024-01-31")

    args, kwargs = cursor.execute.call_args
    sql_text = args[0]
    params = args[1]
    assert "%(start_date)s" in sql_text and "%(end_date)s" in sql_text
    assert params["start_date"] == dt.date(2024, 1, 1)
    assert params["end_date"] == dt.date(2024, 1, 31)
    assert result.total_revenue == 1000.0
    assert result.order_count == 4
    assert result.avg_order_value == 250.0


def test_get_sales_summary_zero_orders_has_zero_avg():
    cursor, get_cursor_cm = _fake_cursor(fetchone_result={"total_revenue": 0.0, "order_count": 0})
    with patch("app.tools.sales.get_cursor", get_cursor_cm):
        result = sales.get_sales_summary("2024-01-01", "2024-01-31")
    assert result.avg_order_value == 0.0


# --- compare_sales_periods ----------------------------------------------


def test_compare_sales_periods_computes_deltas():
    call_results = iter(
        [
            {"total_revenue": 1000.0, "order_count": 10},
            {"total_revenue": 1500.0, "order_count": 12},
        ]
    )
    cursor = MagicMock()
    cursor.fetchone.side_effect = lambda: next(call_results)

    @contextmanager
    def get_cursor_cm():
        yield cursor

    with patch("app.tools.sales.get_cursor", get_cursor_cm):
        comparison = sales.compare_sales_periods(
            "2024-01-01", "2024-01-31", "2024-02-01", "2024-02-29"
        )

    assert comparison.revenue_delta == 500.0
    assert comparison.revenue_delta_pct == 50.0
    assert comparison.order_count_delta == 2


# --- get_product_performance ---------------------------------------------


def test_get_product_performance_rejects_negative_top_n():
    with patch("app.tools.products.get_cursor") as mock_get_cursor:
        with pytest.raises(ToolValidationError):
            products.get_product_performance("2024-01-01", "2024-01-31", top_n=-1)
        mock_get_cursor.assert_not_called()


def test_get_product_performance_rejects_top_n_over_max():
    with patch("app.tools.products.get_cursor") as mock_get_cursor:
        with pytest.raises(ToolValidationError):
            products.get_product_performance("2024-01-01", "2024-01-31", top_n=10_000)
        mock_get_cursor.assert_not_called()


def test_get_product_performance_binds_top_n_param():
    cursor, get_cursor_cm = _fake_cursor(
        fetchall_result=[
            {
                "product_id": 1,
                "sku": "SKU-1",
                "name": "Widget",
                "category": "Widgets",
                "revenue": 100.0,
                "quantity_sold": 5,
            }
        ]
    )
    with patch("app.tools.products.get_cursor", get_cursor_cm):
        result = products.get_product_performance("2024-01-01", "2024-01-31", top_n=5)

    _, params = cursor.execute.call_args[0]
    assert params["top_n"] == 5
    assert result.items[0].sku == "SKU-1"


# --- get_customer_performance ---------------------------------------------


def test_get_customer_performance_valid_call():
    cursor, get_cursor_cm = _fake_cursor(
        fetchall_result=[
            {
                "customer_id": 1,
                "full_name": "Jane Doe",
                "email": "jane@example.com",
                "segment": "high_value",
                "revenue": 500.0,
                "order_count": 3,
            }
        ]
    )
    with patch("app.tools.customers.get_cursor", get_cursor_cm):
        result = customers.get_customer_performance("2024-01-01", "2024-01-31")
    assert result.items[0].full_name == "Jane Doe"


# --- get_transaction_failures ---------------------------------------------


def test_get_transaction_failures_computes_rate():
    cursor, get_cursor_cm = _fake_cursor(
        fetchone_result={"total_transactions": 200, "failed_count": 40}
    )
    with patch("app.tools.transactions.get_cursor", get_cursor_cm):
        result = transactions.get_transaction_failures("2024-04-10", "2024-04-14")
    assert result.failed_rate == 0.2


def test_get_transaction_failures_rejects_inverted_range():
    with patch("app.tools.transactions.get_cursor") as mock_get_cursor:
        with pytest.raises(ToolValidationError):
            transactions.get_transaction_failures("2024-04-14", "2024-04-10")
        mock_get_cursor.assert_not_called()


# --- get_operational_events ---------------------------------------------


def test_get_operational_events_rejects_invalid_severity():
    with patch("app.tools.operations.get_cursor") as mock_get_cursor:
        with pytest.raises(ToolValidationError):
            operations.get_operational_events("2024-04-01", "2024-04-30", severity="catastrophic")
        mock_get_cursor.assert_not_called()


def test_get_operational_events_passes_severity_through():
    cursor, get_cursor_cm = _fake_cursor(fetchall_result=[])
    with patch("app.tools.operations.get_cursor", get_cursor_cm):
        operations.get_operational_events("2024-04-01", "2024-04-30", severity="critical")
    _, params = cursor.execute.call_args[0]
    assert params["severity"] == "critical"
