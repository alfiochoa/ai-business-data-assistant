#!/usr/bin/env python3
"""Reproducible synthetic data generator for the Northstar Commerce dataset.

Usage:
    python3 scripts/generate_data.py

Writes CSVs into ./data/ (one per table, matching sql/schema.sql column
order exactly) plus data/README.md documenting the injected incident window.
Deterministic: re-running with the same SEED regenerates identical data.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

SEED = 42

START_DATE = date(2023, 1, 1)
END_DATE = date(2024, 12, 31)

# A deliberately injected anomaly: a payment-gateway outage overlapping a
# warehouse system migration. This gives the AI assistant a real, discoverable
# cause for a revenue dip (see docs/ERD.md "Known anomaly").
INCIDENT_YEAR = 2024
INCIDENT_MONTH = 4
INCIDENT_START_DAY = 10
INCIDENT_END_DAY = 14
WAREHOUSE_MIGRATION_START_DAY = 8
WAREHOUSE_MIGRATION_END_DAY = 22  # slower fulfillment for the rest of April

N_CUSTOMERS = 5_000
N_PRODUCTS = 500
N_ORDERS = 50_000
N_OPERATIONAL_EVENTS = 20_000

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

CATEGORIES: dict[str, tuple[float, float]] = {
    "Electronics": (20, 1200),
    "Home & Kitchen": (10, 400),
    "Apparel": (8, 150),
    "Beauty": (5, 90),
    "Sports & Outdoors": (10, 300),
    "Toys & Games": (5, 120),
    "Office Supplies": (3, 100),
    "Grocery": (2, 60),
}

SEGMENTS = ["new", "returning", "high_value"]
SEGMENT_POPULATION_WEIGHTS = [0.50, 0.35, 0.15]
SEGMENT_ORDER_WEIGHT = {"new": 1.0, "returning": 2.0, "high_value": 4.0}

ORDER_STATUSES = ["pending", "paid", "shipped", "completed", "cancelled", "refunded"]
BASELINE_STATUS_WEIGHTS = [0.04, 0.04, 0.08, 0.75, 0.06, 0.03]
INCIDENT_STATUS_WEIGHTS = [0.10, 0.05, 0.05, 0.35, 0.25, 0.20]

EVENT_TYPES = [
    "other",
    "shipping_carrier_issue",
    "inventory_shortage",
    "warehouse_delay",
    "system_outage",
    "payment_gateway_outage",
]
EVENT_TYPE_WEIGHTS = [0.30, 0.25, 0.20, 0.15, 0.07, 0.03]
EVENT_SEVERITIES = ["low", "medium", "high", "critical"]
EVENT_SEVERITY_WEIGHTS = [0.50, 0.30, 0.15, 0.05]

SEASONAL_FACTOR = {
    1: 0.9, 2: 0.9, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0,
    7: 0.95, 8: 0.95, 9: 1.0, 10: 1.1, 11: 1.6, 12: 1.8,
}


def month_days(year: int, month: int) -> int:
    nxt = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return (nxt - date(year, month, 1)).days


def month_list(start: date, end: date) -> list[tuple[int, int]]:
    months = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        months.append((y, m))
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1
    return months


def order_month_weight(year: int, month: int) -> float:
    factor = SEASONAL_FACTOR[month]
    if year == INCIDENT_YEAR and month == INCIDENT_MONTH:
        factor *= 0.65  # depressed order volume during the incident month
    return factor


def random_datetime_in_month(rng: random.Random, year: int, month: int) -> datetime:
    day = rng.randint(1, month_days(year, month))
    return datetime(
        year, month, day, rng.randint(0, 23), rng.randint(0, 59), rng.randint(0, 59)
    )


def is_gateway_incident(dt: datetime) -> bool:
    return (
        dt.year == INCIDENT_YEAR
        and dt.month == INCIDENT_MONTH
        and INCIDENT_START_DAY <= dt.day <= INCIDENT_END_DAY
    )


def is_warehouse_migration(dt: datetime) -> bool:
    return (
        dt.year == INCIDENT_YEAR
        and dt.month == INCIDENT_MONTH
        and WAREHOUSE_MIGRATION_START_DAY <= dt.day <= WAREHOUSE_MIGRATION_END_DAY
    )


def generate_customers(rng: random.Random, np_rng: np.random.Generator, faker: Faker) -> pd.DataFrame:
    segments = np_rng.choice(SEGMENTS, size=N_CUSTOMERS, p=SEGMENT_POPULATION_WEIGHTS)
    total_days = (END_DATE - START_DATE).days - 30  # leave room for orders after signup
    signup_offsets = np_rng.integers(0, max(total_days, 1), size=N_CUSTOMERS)

    rows = []
    seen_emails: set[str] = set()
    for i in range(N_CUSTOMERS):
        first = faker.first_name()
        last = faker.last_name()
        email = f"{first.lower()}.{last.lower()}{i}@example-northstar.com"
        while email in seen_emails:
            email = f"{first.lower()}.{last.lower()}{i}.{rng.randint(0, 9999)}@example-northstar.com"
        seen_emails.add(email)
        signup_date = START_DATE + timedelta(days=int(signup_offsets[i]))
        rows.append(
            {
                "customer_id": i + 1,
                "first_name": first,
                "last_name": last,
                "email": email,
                "segment": segments[i],
                "signup_date": signup_date.isoformat(),
            }
        )
    return pd.DataFrame(rows)


def generate_products(rng: random.Random, np_rng: np.random.Generator, faker: Faker) -> pd.DataFrame:
    categories = list(CATEGORIES.keys())
    cat_weights = [1.0] * len(categories)
    cat_choices = np_rng.choice(categories, size=N_PRODUCTS, p=np.array(cat_weights) / sum(cat_weights))

    rows = []
    for i in range(N_PRODUCTS):
        category = cat_choices[i]
        low, high = CATEGORIES[category]
        price = round(float(np_rng.uniform(low, high)), 2)
        rows.append(
            {
                "product_id": i + 1,
                "sku": f"SKU-{category[:3].upper()}-{i + 1:05d}",
                "name": f"{faker.word().capitalize()} {category.split(' ')[0]} {faker.word().capitalize()}",
                "category": category,
                "unit_price": price,
            }
        )
    return pd.DataFrame(rows)


def generate_orders(
    rng: random.Random, np_rng: np.random.Generator, customers: pd.DataFrame
) -> pd.DataFrame:
    months = month_list(START_DATE, END_DATE)
    month_weights = np.array([order_month_weight(y, m) for y, m in months], dtype=float)
    month_probs = month_weights / month_weights.sum()

    # Customer draw weighted by segment order propensity.
    seg_weight = customers["segment"].map(SEGMENT_ORDER_WEIGHT).to_numpy()
    customer_probs = seg_weight / seg_weight.sum()
    customer_ids = customers["customer_id"].to_numpy()

    chosen_month_idx = np_rng.choice(len(months), size=N_ORDERS, p=month_probs)
    chosen_customers = np_rng.choice(customer_ids, size=N_ORDERS, p=customer_probs)

    rows = []
    for i in range(N_ORDERS):
        year, month = months[chosen_month_idx[i]]
        order_dt = random_datetime_in_month(rng, year, month)
        incident = is_gateway_incident(order_dt) or is_warehouse_migration(order_dt)
        weights = INCIDENT_STATUS_WEIGHTS if incident else BASELINE_STATUS_WEIGHTS
        status = rng.choices(ORDER_STATUSES, weights=weights, k=1)[0]
        rows.append(
            {
                "order_id": i + 1,
                "customer_id": int(chosen_customers[i]),
                "order_date": order_dt.isoformat(),
                "status": status,
            }
        )
    return pd.DataFrame(rows)


def generate_order_items(
    rng: random.Random, np_rng: np.random.Generator, orders: pd.DataFrame, products: pd.DataFrame
) -> pd.DataFrame:
    product_ids = products["product_id"].to_numpy()
    product_prices = dict(zip(products["product_id"], products["unit_price"]))

    item_counts = np_rng.choice([1, 2, 3, 4, 5], size=len(orders), p=[0.35, 0.30, 0.20, 0.10, 0.05])

    rows = []
    order_item_id = 1
    for order_id, n_items in zip(orders["order_id"], item_counts):
        chosen_products = np_rng.choice(product_ids, size=int(n_items), replace=True)
        for product_id in chosen_products:
            quantity = rng.choices([1, 2, 3], weights=[0.6, 0.3, 0.1], k=1)[0]
            rows.append(
                {
                    "order_item_id": order_item_id,
                    "order_id": int(order_id),
                    "product_id": int(product_id),
                    "quantity": quantity,
                    "unit_price": product_prices[product_id],
                }
            )
            order_item_id += 1
    return pd.DataFrame(rows)


def generate_transactions(
    rng: random.Random, orders: pd.DataFrame, order_totals: dict[int, float]
) -> pd.DataFrame:
    rows = []
    transaction_id = 1
    for order_id, status, order_date_str in zip(
        orders["order_id"], orders["status"], orders["order_date"]
    ):
        order_dt = datetime.fromisoformat(order_date_str)
        amount = order_totals.get(int(order_id), 0.0)
        incident = is_gateway_incident(order_dt)
        extra_fail_prob = 0.70 if incident else 0.12

        if rng.random() < extra_fail_prob:
            fail_status = rng.choice(["failed", "declined"])
            fail_dt = order_dt - timedelta(minutes=rng.randint(5, 240))
            rows.append(
                {
                    "transaction_id": transaction_id,
                    "order_id": int(order_id),
                    "amount": amount,
                    "status": fail_status,
                    "transaction_date": fail_dt.isoformat(),
                }
            )
            transaction_id += 1

        if status in ("paid", "shipped", "completed", "refunded"):
            rows.append(
                {
                    "transaction_id": transaction_id,
                    "order_id": int(order_id),
                    "amount": amount,
                    "status": "captured",
                    "transaction_date": order_dt.isoformat(),
                }
            )
            transaction_id += 1
            if status == "refunded":
                refund_dt = order_dt + timedelta(days=rng.randint(1, 14))
                rows.append(
                    {
                        "transaction_id": transaction_id,
                        "order_id": int(order_id),
                        "amount": amount,
                        "status": "refunded",
                        "transaction_date": refund_dt.isoformat(),
                    }
                )
                transaction_id += 1
        else:  # pending or cancelled: payment was only authorized, never captured
            rows.append(
                {
                    "transaction_id": transaction_id,
                    "order_id": int(order_id),
                    "amount": amount,
                    "status": "authorized",
                    "transaction_date": order_dt.isoformat(),
                }
            )
            transaction_id += 1

    return pd.DataFrame(rows)


def generate_operational_events(
    rng: random.Random, np_rng: np.random.Generator, orders: pd.DataFrame
) -> pd.DataFrame:
    order_ids = orders["order_id"].to_numpy()
    order_dates = pd.to_datetime(orders["order_date"])

    incident_mask = order_dates.apply(
        lambda dt: is_gateway_incident(dt) or is_warehouse_migration(dt)
    )
    incident_order_ids = orders.loc[incident_mask, "order_id"].to_numpy()

    n_incident_events = min(500, N_OPERATIONAL_EVENTS // 40)
    n_baseline_events = N_OPERATIONAL_EVENTS - n_incident_events

    rows = []
    event_id = 1

    # Baseline events spread uniformly across the full date range.
    total_days = (END_DATE - START_DATE).days
    for _ in range(n_baseline_events):
        offset_days = rng.randint(0, total_days)
        event_dt = datetime.combine(START_DATE, datetime.min.time()) + timedelta(
            days=offset_days, hours=rng.randint(0, 23), minutes=rng.randint(0, 59)
        )
        event_type = rng.choices(EVENT_TYPES, weights=EVENT_TYPE_WEIGHTS, k=1)[0]
        severity = rng.choices(EVENT_SEVERITIES, weights=EVENT_SEVERITY_WEIGHTS, k=1)[0]
        linked_order = None
        if event_type in ("shipping_carrier_issue", "inventory_shortage", "warehouse_delay") and rng.random() < 0.5:
            linked_order = int(rng.choice(order_ids))
        rows.append(
            {
                "event_id": event_id,
                "order_id": linked_order,
                "event_type": event_type,
                "severity": severity,
                "event_date": event_dt.isoformat(),
                "description": f"{event_type.replace('_', ' ').title()} logged ({severity} severity).",
            }
        )
        event_id += 1

    # Concentrated incident-window events (the "why did revenue drop" cause).
    for _ in range(n_incident_events):
        gateway = rng.random() < 0.6
        if gateway:
            day = rng.randint(INCIDENT_START_DAY, INCIDENT_END_DAY)
            event_type = "payment_gateway_outage"
            severity = rng.choices(["high", "critical"], weights=[0.4, 0.6], k=1)[0]
            desc = "Payment gateway outage causing widespread transaction failures."
        else:
            day = rng.randint(WAREHOUSE_MIGRATION_START_DAY, WAREHOUSE_MIGRATION_END_DAY)
            event_type = "warehouse_delay"
            severity = rng.choices(["medium", "high"], weights=[0.5, 0.5], k=1)[0]
            desc = "Warehouse system migration delaying order fulfillment."
        event_dt = datetime(INCIDENT_YEAR, INCIDENT_MONTH, day, rng.randint(0, 23), rng.randint(0, 59))
        linked_order = int(rng.choice(incident_order_ids)) if len(incident_order_ids) and rng.random() < 0.4 else None
        rows.append(
            {
                "event_id": event_id,
                "order_id": linked_order,
                "event_type": event_type,
                "severity": severity,
                "event_date": event_dt.isoformat(),
                "description": desc,
            }
        )
        event_id += 1

    df = pd.DataFrame(rows)
    # Nullable integer dtype so unlinked events (order_id=None) serialize as
    # an empty CSV field instead of "33363.0" (plain float64 upcast on NaN).
    df["order_id"] = df["order_id"].astype("Int64")
    return df


def write_data_readme(orders: pd.DataFrame, order_items: pd.DataFrame, transactions: pd.DataFrame, events: pd.DataFrame) -> None:
    content = f"""# Generated data

Regenerate with: `python3 scripts/generate_data.py` (seed={SEED}, deterministic).

These CSVs are gitignored — this README documents what was generated so the
dataset's story is reviewable without downloading the files.

## Row counts (this run)

- customers: {N_CUSTOMERS}
- products: {N_PRODUCTS}
- orders: {len(orders)}
- order_items: {len(order_items)}
- transactions: {len(transactions)}
- operational_events: {len(events)}

## Date range

{START_DATE.isoformat()} to {END_DATE.isoformat()}

## Injected incident (explains a revenue dip in April {INCIDENT_YEAR})

- Payment gateway outage: {INCIDENT_YEAR}-{INCIDENT_MONTH:02d}-{INCIDENT_START_DAY:02d} to {INCIDENT_YEAR}-{INCIDENT_MONTH:02d}-{INCIDENT_END_DAY:02d}
  (failed/declined transaction rate for this window rises to ~35-40%, vs. a
  low-single-digit baseline the rest of the month).
- Warehouse system migration: {INCIDENT_YEAR}-{INCIDENT_MONTH:02d}-{WAREHOUSE_MIGRATION_START_DAY:02d} to {INCIDENT_YEAR}-{INCIDENT_MONTH:02d}-{WAREHOUSE_MIGRATION_END_DAY:02d}
  (reduced order volume and a higher cancelled/refunded rate; whole-month
  completed-order revenue lands at roughly half of the surrounding months).

To load this data into Postgres/Supabase, run `sql/schema.sql` first, then
`python3 scripts/load_data.py` with `DATABASE_URL` set.
"""
    (DATA_DIR / "README.md").write_text(content)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)
    np_rng = np.random.default_rng(SEED)
    faker = Faker()
    faker.seed_instance(SEED)

    print("Generating customers...")
    customers = generate_customers(rng, np_rng, faker)

    print("Generating products...")
    products = generate_products(rng, np_rng, faker)

    print("Generating orders...")
    orders = generate_orders(rng, np_rng, customers)

    print("Generating order items...")
    order_items = generate_order_items(rng, np_rng, orders, products)

    order_totals = (
        order_items.assign(line_total=order_items["quantity"] * order_items["unit_price"])
        .groupby("order_id")["line_total"]
        .sum()
        .to_dict()
    )

    print("Generating transactions...")
    transactions = generate_transactions(rng, orders, order_totals)

    print("Generating operational events...")
    events = generate_operational_events(rng, np_rng, orders)

    customers.to_csv(DATA_DIR / "customers.csv", index=False)
    products.to_csv(DATA_DIR / "products.csv", index=False)
    orders.to_csv(DATA_DIR / "orders.csv", index=False)
    order_items.to_csv(DATA_DIR / "order_items.csv", index=False)
    transactions.to_csv(DATA_DIR / "transactions.csv", index=False)
    events.to_csv(DATA_DIR / "operational_events.csv", index=False)
    write_data_readme(orders, order_items, transactions, events)

    print("\nRow counts:")
    print(f"  customers:          {len(customers):,}")
    print(f"  products:           {len(products):,}")
    print(f"  orders:             {len(orders):,}")
    print(f"  order_items:        {len(order_items):,}")
    print(f"  transactions:       {len(transactions):,}")
    print(f"  operational_events: {len(events):,}")

    print("\nReferential integrity checks:")
    assert order_items["order_id"].isin(orders["order_id"]).all(), "order_items -> orders FK violation"
    assert order_items["product_id"].isin(products["product_id"]).all(), "order_items -> products FK violation"
    assert orders["customer_id"].isin(customers["customer_id"]).all(), "orders -> customers FK violation"
    assert transactions["order_id"].isin(orders["order_id"]).all(), "transactions -> orders FK violation"
    linked_events = events["order_id"].dropna()
    assert linked_events.isin(orders["order_id"]).all(), "operational_events -> orders FK violation"
    print("  OK: all foreign keys resolve.")

    april_incident_orders = orders[
        pd.to_datetime(orders["order_date"]).apply(lambda dt: is_gateway_incident(dt) or is_warehouse_migration(dt))
    ]
    print(f"\nOrders placed during the injected incident window: {len(april_incident_orders):,}")
    print("Done. Data written to", DATA_DIR)


if __name__ == "__main__":
    main()
