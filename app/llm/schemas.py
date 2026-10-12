"""OpenAI function-calling tool schemas — one entry per app.tools.registry function.

Keep these in exact 1:1 correspondence with app.tools.registry.TOOL_REGISTRY;
tests/test_llm_tool_schemas.py enforces that at import time.
"""

from __future__ import annotations

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_sales_summary",
            "description": (
                "Get total recognized revenue, order count, and average order value "
                "for Northstar Goods over a date range. Use this for any question "
                "about total sales/revenue in a period."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "format": "date", "description": "Inclusive start date, YYYY-MM-DD."},
                    "end_date": {"type": "string", "format": "date", "description": "Inclusive end date, YYYY-MM-DD."},
                },
                "required": ["start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_sales_periods",
            "description": (
                "Compare revenue and order count between two explicit date ranges. "
                "Use this for any 'compare X to Y' or 'how did this month do vs last month' question."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "period_a_start": {"type": "string", "format": "date"},
                    "period_a_end": {"type": "string", "format": "date"},
                    "period_b_start": {"type": "string", "format": "date"},
                    "period_b_end": {"type": "string", "format": "date"},
                },
                "required": ["period_a_start", "period_a_end", "period_b_start", "period_b_end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_performance",
            "description": (
                "Get the top-selling products by revenue for a date range. "
                "Use this for 'which products generated the most revenue' style questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"},
                    "top_n": {"type": "integer", "minimum": 1, "maximum": 100, "description": "How many top products to return, default 10."},
                },
                "required": ["start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_performance",
            "description": (
                "Get the top customers by revenue for a date range, including how many "
                "orders they placed. Use this for 'which customers spent the most / ordered the most' questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"},
                    "top_n": {"type": "integer", "minimum": 1, "maximum": 100, "description": "How many top customers to return, default 10."},
                },
                "required": ["start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_transaction_failures",
            "description": (
                "Get the count and rate of failed/declined payment transactions for a date range. "
                "Use this for 'failed transactions', 'declined payments', or payment-reliability questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"},
                },
                "required": ["start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_operational_events",
            "description": (
                "Get logged operational incidents (e.g. payment gateway outages, warehouse "
                "delays, shipping issues) for a date range, optionally filtered by severity. "
                "Use this to explain WHY a sales/revenue/transaction metric looks unusual for a period."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"},
                    "severity": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "Optional minimum-interest severity filter.",
                    },
                },
                "required": ["start_date", "end_date"],
            },
        },
    },
]

TOOL_NAMES = {schema["function"]["name"] for schema in TOOL_SCHEMAS}
