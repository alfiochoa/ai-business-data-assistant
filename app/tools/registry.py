"""Single source of truth mapping a tool name to its callable.

Both the LLM layer (to dispatch a model's tool call) and the test suite (to
confirm every tool has a matching schema) import from here, so the two never
drift apart.
"""

from __future__ import annotations

from typing import Callable

from app.tools.customers import get_customer_performance
from app.tools.operations import get_operational_events
from app.tools.products import get_product_performance
from app.tools.sales import compare_sales_periods, get_sales_summary
from app.tools.transactions import get_transaction_failures

TOOL_REGISTRY: dict[str, Callable] = {
    "get_sales_summary": get_sales_summary,
    "compare_sales_periods": compare_sales_periods,
    "get_product_performance": get_product_performance,
    "get_customer_performance": get_customer_performance,
    "get_transaction_failures": get_transaction_failures,
    "get_operational_events": get_operational_events,
}
