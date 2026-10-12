# Security notes

This is a demo over **synthetic data**, but it is built as if it were real.

- **No SQL from the model.** The LLM can only call six validated tool functions;
  all SQL is parameterized (see README, "Why this design").
- **Use a read-only database role for the app.** The app only runs `SELECT`s, so
  it should not connect as `postgres`/an owner. `sql/readonly_role.sql` creates
  `app_readonly` (SELECT-only, `default_transaction_read_only`, 10s statement
  timeout, connection limit). Use an admin connection only for
  `schema.sql` and `scripts/load_data.py`; give the deployed app the
  `app_readonly` `DATABASE_URL`. Defense in depth: even a bug in a tool cannot write or drop data.
- **Secrets** (`DATABASE_URL`, `LLM_API_KEY`, `LLM_FALLBACK_*`, `HF_TOKEN`) live
  only in `.env` (gitignored) or the host's secret store (Streamlit Cloud
  secrets). History was scanned (2026-10-12): `.env` was never committed and
  no real key, token or DB password appears in any commit; only placeholders.
- **Rotate** any key that was ever pasted into a chat, log or screenshot.
- **Public demo caveats:** the UI has no authentication or per-user rate
  limiting; a public deployment spends your free LLM quota. Add auth/limits
  before using real data.

Report issues via a GitHub issue (no sensitive details) or to the repo owner.
