# Generated data

Regenerate with: `python3 scripts/generate_data.py` (seed=42, deterministic).

These CSVs are gitignored — this README documents what was generated so the
dataset's story is reviewable without downloading the files.

## Row counts (this run)

- customers: 5000
- products: 500
- orders: 50000
- order_items: 109942
- transactions: 57834
- operational_events: 20000

## Date range

2023-01-01 to 2024-12-31

## Injected incident (explains a revenue dip in April 2024)

- Payment gateway outage: 2024-04-10 to 2024-04-14
  (failed/declined transaction rate for this window rises to ~35-40%, vs. a
  low-single-digit baseline the rest of the month).
- Warehouse system migration: 2024-04-08 to 2024-04-22
  (reduced order volume and a higher cancelled/refunded rate; whole-month
  completed-order revenue lands at roughly half of the surrounding months).

To load this data into Postgres/Supabase, run `sql/schema.sql` first, then
`python3 scripts/load_data.py` with `DATABASE_URL` set.
