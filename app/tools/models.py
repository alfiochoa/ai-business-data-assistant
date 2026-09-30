"""Structured, typed results returned by every business tool.

The LLM layer never sees raw DB rows — it sees these models (serialized to
JSON), and the API/UI layer can render them directly without re-deriving
anything from a tool's internal SQL.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class SalesSummary(BaseModel):
    start_date: dt.date
    end_date: dt.date
    total_revenue: float
    order_count: int
    avg_order_value: float


class PeriodComparison(BaseModel):
    period_a: SalesSummary
    period_b: SalesSummary
    revenue_delta: float
    revenue_delta_pct: float | None
    order_count_delta: int


class ProductPerformanceItem(BaseModel):
    product_id: int
    sku: str
    name: str
    category: str
    revenue: float
    quantity_sold: int


class ProductPerformance(BaseModel):
    start_date: dt.date
    end_date: dt.date
    items: list[ProductPerformanceItem]


class CustomerPerformanceItem(BaseModel):
    customer_id: int
    full_name: str
    email: str
    segment: str
    revenue: float
    order_count: int


class CustomerPerformance(BaseModel):
    start_date: dt.date
    end_date: dt.date
    items: list[CustomerPerformanceItem]


class TransactionFailureSummary(BaseModel):
    start_date: dt.date
    end_date: dt.date
    total_transactions: int
    failed_count: int
    failed_rate: float


class OperationalEvent(BaseModel):
    event_id: int
    order_id: int | None
    event_type: str
    severity: str
    event_date: dt.datetime
    description: str


class OperationalEventsResult(BaseModel):
    start_date: dt.date
    end_date: dt.date
    severity_filter: str | None
    events: list[OperationalEvent]
