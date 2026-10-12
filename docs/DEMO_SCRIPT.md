# 60-second demo video script

Setup: UI open at the live URL (or `streamlit run streamlit_app.py`), "Example
questions" collapsed, browser zoom ~110%. All data is synthetic (Northstar Goods).

| Time | Say | Do / ask (type exactly) |
|---|---|---|
| 0:00–0:08 | "Meet Northstar Goods, a fictional small online store losing money to failed payments. The owner has no analyst and no SQL." | Show the title and disclaimer. |
| 0:08–0:25 | "I just ask in plain English." | `Compare revenue between March 2024 and April 2024 and explain the change` → Ask. Point at the figures (about -50.66% revenue) and the payment-gateway outage on April 10. |
| 0:25–0:38 | "Every number is verified, not invented." | Expand **How this was answered**: show the tool calls and the structured result from PostgreSQL. |
| 0:38–0:50 | "It can quantify the leak." | `How many payments failed in April 2024 versus March 2024, and what likely caused the difference?` (expect 238 vs 269 failures, 10.6% vs 15.8%). |
| 0:50–0:57 | "And it stays in scope." | `What's the weather tomorrow in Madrid?` → polite refusal, no tools called. |
| 0:57–1:00 | "LLM → controlled tools → parameterized SQL → Postgres. Free stack: Groq, Supabase, Streamlit. Code on GitHub." | Show the repo URL. |

Tips: run each question once beforehand so Groq's free tier is warm; if a rate
limit appears the app falls back to a second model automatically, so just wait a
few seconds and re-ask.
