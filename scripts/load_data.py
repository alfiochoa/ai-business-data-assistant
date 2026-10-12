#!/usr/bin/env python3
"""Load the generated CSVs (see scripts/generate_data.py) into Postgres.

Usage:
    DATABASE_URL=postgresql://... python3 scripts/load_data.py

Requires sql/schema.sql to already be applied to the target database.
Tables are loaded in FK-safe order and truncated first (idempotent re-runs).
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Order matters: parents before children.
TABLES_IN_LOAD_ORDER = [
    "customers",
    "products",
    "orders",
    "order_items",
    "transactions",
    "operational_events",
]


def load_table(cur, table: str) -> int:
    csv_path = DATA_DIR / f"{table}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"{csv_path} not found. Run `python3 scripts/generate_data.py` first."
        )
    with csv_path.open("r", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        columns = ", ".join(header)
        copy_sql = f"COPY {table} ({columns}) FROM STDIN WITH (FORMAT csv, NULL '')"
        cur.copy_expert(copy_sql, f)
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    return cur.fetchone()[0]


def main() -> None:
    load_dotenv()  # so DATABASE_URL from .env works as the README describes
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: set DATABASE_URL to your Supabase/Postgres connection string.", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(database_url)
    try:
        with conn:
            with conn.cursor() as cur:
                print("Truncating existing data (FK-safe order, reversed)...")
                cur.execute(
                    "TRUNCATE " + ", ".join(reversed(TABLES_IN_LOAD_ORDER)) + " RESTART IDENTITY CASCADE"
                )
                for table in TABLES_IN_LOAD_ORDER:
                    print(f"Loading {table}...")
                    count = load_table(cur, table)
                    print(f"  {table}: {count:,} rows")
    finally:
        conn.close()

    print("Load complete.")


if __name__ == "__main__":
    main()
