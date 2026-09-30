-- AI Business Data Assistant — Northstar Commerce schema
-- Target: PostgreSQL 14+ (developed against Supabase-hosted Postgres)
--
-- Business definitions encoded here (see also PROJECT_SPEC.md / docs/ERD.md):
--   * Revenue           = SUM(order_items.quantity * order_items.unit_price)
--                         for orders whose status is in ('paid','shipped','completed').
--                         cancelled/refunded orders and pending orders contribute
--                         zero revenue.
--   * Failed transaction = a transactions row with status 'failed' or 'declined'.
--   * Operational event  = a logged incident, optionally tied to a specific order,
--                         used to explain anomalies (e.g. a revenue dip).

BEGIN;

CREATE TYPE customer_segment AS ENUM ('new', 'returning', 'high_value');

CREATE TYPE order_status AS ENUM (
    'pending',    -- order placed, payment not yet confirmed
    'paid',       -- payment captured, awaiting fulfillment
    'shipped',    -- fulfilled and shipped
    'completed',  -- delivered / closed out successfully
    'cancelled',  -- cancelled before fulfillment, no revenue
    'refunded'    -- fulfilled then refunded, no net revenue
);

CREATE TYPE transaction_status AS ENUM (
    'authorized',
    'captured',
    'failed',
    'declined',
    'refunded'
);

CREATE TYPE operational_event_type AS ENUM (
    'payment_gateway_outage',
    'warehouse_delay',
    'shipping_carrier_issue',
    'inventory_shortage',
    'system_outage',
    'other'
);

CREATE TYPE operational_event_severity AS ENUM ('low', 'medium', 'high', 'critical');

CREATE TABLE customers (
    customer_id     BIGSERIAL PRIMARY KEY,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    segment         customer_segment NOT NULL DEFAULT 'new',
    signup_date     DATE NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_customers_segment ON customers (segment);

CREATE TABLE products (
    product_id      BIGSERIAL PRIMARY KEY,
    sku             TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    category        TEXT NOT NULL,
    unit_price      NUMERIC(10, 2) NOT NULL CHECK (unit_price > 0),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_products_category ON products (category);

CREATE TABLE orders (
    order_id        BIGSERIAL PRIMARY KEY,
    customer_id     BIGINT NOT NULL REFERENCES customers (customer_id),
    order_date      TIMESTAMPTZ NOT NULL,
    status          order_status NOT NULL DEFAULT 'pending',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_orders_customer_id ON orders (customer_id);
CREATE INDEX idx_orders_order_date ON orders (order_date);
CREATE INDEX idx_orders_status ON orders (status);

CREATE TABLE order_items (
    order_item_id   BIGSERIAL PRIMARY KEY,
    order_id        BIGINT NOT NULL REFERENCES orders (order_id),
    product_id      BIGINT NOT NULL REFERENCES products (product_id),
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    -- Snapshot of the unit price at time of sale (may differ from the
    -- product's current price) so historical revenue never drifts.
    unit_price      NUMERIC(10, 2) NOT NULL CHECK (unit_price > 0)
);

CREATE INDEX idx_order_items_order_id ON order_items (order_id);
CREATE INDEX idx_order_items_product_id ON order_items (product_id);

CREATE TABLE transactions (
    transaction_id      BIGSERIAL PRIMARY KEY,
    order_id            BIGINT NOT NULL REFERENCES orders (order_id),
    amount              NUMERIC(10, 2) NOT NULL CHECK (amount >= 0),
    status              transaction_status NOT NULL,
    transaction_date    TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_transactions_order_id ON transactions (order_id);
CREATE INDEX idx_transactions_status ON transactions (status);
CREATE INDEX idx_transactions_transaction_date ON transactions (transaction_date);

CREATE TABLE operational_events (
    event_id        BIGSERIAL PRIMARY KEY,
    -- Nullable: many operational events (e.g. a platform-wide outage) are not
    -- tied to one specific order.
    order_id        BIGINT REFERENCES orders (order_id),
    event_type      operational_event_type NOT NULL,
    severity        operational_event_severity NOT NULL,
    event_date      TIMESTAMPTZ NOT NULL,
    description     TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_operational_events_event_date ON operational_events (event_date);
CREATE INDEX idx_operational_events_order_id ON operational_events (order_id);
CREATE INDEX idx_operational_events_type ON operational_events (event_type);

-- Convenience view: per-order revenue, honoring the revenue definition above.
CREATE VIEW v_order_revenue AS
SELECT
    o.order_id,
    o.customer_id,
    o.order_date,
    o.status,
    COALESCE(SUM(oi.quantity * oi.unit_price), 0)::NUMERIC(12, 2) AS order_revenue
FROM orders o
LEFT JOIN order_items oi ON oi.order_id = o.order_id
GROUP BY o.order_id, o.customer_id, o.order_date, o.status;

COMMENT ON VIEW v_order_revenue IS
    'Per-order revenue. Business tools should filter WHERE status IN (''paid'',''shipped'',''completed'') to get recognized revenue.';

COMMIT;
