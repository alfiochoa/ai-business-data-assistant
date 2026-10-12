"""Streamlit chat UI for the Northstar Goods Payment Loss Assistant.

If API_BASE_URL is set, talks to the FastAPI backend over HTTP (the full
UI -> API -> LLM -> tools -> Postgres architecture). Otherwise (e.g. Streamlit
Community Cloud) it calls the same assistant in-process, with secrets read
from st.secrets or the environment.
"""

from __future__ import annotations

import os

import requests
import streamlit as st

try:  # Streamlit Cloud secrets -> env, so app.llm / app.database pick them up
    for _k in st.secrets:
        if isinstance(st.secrets[_k], str):
            os.environ.setdefault(_k, st.secrets[_k])
except Exception:
    pass

API_BASE_URL = os.environ.get("API_BASE_URL")


def ask_backend(question: str) -> tuple[int, dict]:
    """Return (status_code, json) from the HTTP API, or from the in-process assistant."""
    if API_BASE_URL:
        resp = requests.post(f"{API_BASE_URL}/ask", json={"question": question}, timeout=60)
        return resp.status_code, resp.json()
    from app.llm.assistant import answer_question

    try:
        return 200, answer_question(question).model_dump(mode="json")
    except RuntimeError as exc:
        return 503, {"detail": str(exc)}


st.set_page_config(page_title="Northstar Goods — Payment Loss Assistant", page_icon="📊")

st.title("💳 Northstar Goods — Where is my money going?")
st.caption(
    "Fictional portfolio demo of a small online store losing money to payment "
    "failures, refunds and chargebacks. Northstar Goods is not a real company; all "
    "data is synthetic. Answers come only from controlled database tools — "
    "the AI never invents business numbers."
)

EXAMPLES = [
    "How much revenue did failed payments cost us in April 2024?",
    "Which products generated the most revenue?",
    "Why did sales decrease in the second half of April?",
    "Which customers had the highest number of failed transactions?",
    "Compare revenue between January and February 2024.",
]

st.markdown("**Try an example:**")
for i, example in enumerate(EXAMPLES):
    if st.button(example, key=f"ex{i}"):
        st.session_state["pending_question"] = example

with st.form("ask_form"):
    typed = st.text_input("Ask a question about Northstar Goods' payments and sales:")
    ask_clicked = st.form_submit_button("Ask", type="primary")

question = st.session_state.pop("pending_question", None) or (typed if ask_clicked else "")

if question.strip():
    st.caption(f"Question: {question}")
    with st.spinner("Thinking..."):
        try:
            status, data = ask_backend(question)
        except requests.RequestException as exc:
            st.error(f"Could not reach the API at {API_BASE_URL}: {exc}")
            st.stop()
        except Exception as exc:  # e.g. database unreachable
            st.error(f"Something went wrong: {type(exc).__name__}: {exc}")
            st.stop()

    if status == 503:
        st.warning(data.get("detail", "The assistant is not configured yet."))
    elif status >= 400:
        st.error(f"Request failed ({status}): {data}")
    elif not (data.get("answer") or "").strip():
        st.error("The assistant returned an empty answer. Please try again or rephrase.")
    else:
        st.markdown("### Answer")
        st.markdown(data["answer"].replace("$", "\\$"))

        tool_calls = data.get("tool_calls", [])
        if tool_calls:
            with st.expander(f"How this was answered ({len(tool_calls)} tool call(s))", expanded=False):
                for call in tool_calls:
                    st.markdown(f"**Tool:** `{call['tool_name']}`")
                    st.markdown("Arguments:")
                    st.json(call["arguments"])
                    if call.get("error"):
                        st.error(call["error"])
                    else:
                        st.markdown("Structured result from PostgreSQL:")
                        st.json(call["result"])
elif ask_clicked:
    st.warning("Please enter a question first.")
