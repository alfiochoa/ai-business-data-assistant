# AI Business Data Assistant

## Fictional Company
Northstar Goods

## Industry
E-commerce / Retail

## Team
Operations Analytics

## Disclaimer

This is a fictional portfolio demonstration project. Northstar Goods is not a
real company, and no real client data or business results are represented here.
All data is synthetic and generated programmatically.

## Problem

Non-technical operations managers have access to large amounts of
business data but cannot easily query or interpret it without SQL
or analyst support.

## Solution

Build an AI-powered natural-language interface that allows users
to ask questions about sales, customers, transactions, products,
and operational events.

The AI retrieves verified information from PostgreSQL through
controlled business tools and explains the results in natural
language. PostgreSQL remains the source of truth; the LLM is never
allowed to invent business numbers or run arbitrary SQL.

## Primary Users

- Operations managers
- Business analysts
- Non-technical business users

## Example Questions (in scope)

- What were our total sales in March?
- Which products generated the most revenue?
- Why did sales decrease in the second half of April?
- Which customers had the highest number of failed transactions?
- Compare revenue between January and February.
- What were the main operational issues last month?

## Out of Scope

- Anything not derivable from the `customers`, `products`, `orders`,
  `order_items`, `transactions`, and `operational_events` tables
  (e.g. weather, external market data, real-time inventory).
- Free-form/arbitrary SQL execution requested via natural language.
- Predictive forecasting (this is a reporting/explanation assistant,
  not a forecasting engine).

## Key Business Definitions

- **Revenue**: sum of `order_items.unit_price * order_items.quantity`
  for orders with a completed/paid status.
- **Failed transaction**: a `transactions` row with status `failed` or
  `declined`.
- **Operational event**: a logged incident (e.g. warehouse delay,
  payment gateway outage) tied to an order or time period.
- **Period comparison**: revenue/order metrics compared across two
  explicit date ranges supplied by the user or resolved from the
  question.

## Core Technologies

- Python
- PostgreSQL (hosted on Supabase)
- FastAPI
- Streamlit
- OpenAI API (function/tool calling, structured outputs)
- SQL
- REST API
- Git/GitHub

## Architecture (high level)

```
User → Streamlit UI → FastAPI → LLM → controlled business tool
     → validated parameters → known SQL → PostgreSQL (Supabase)
     → structured result → LLM explanation → User
```

## Status

Stage 1 (business scenario) — complete.
Stage 2 (data model / ERD) — next.
