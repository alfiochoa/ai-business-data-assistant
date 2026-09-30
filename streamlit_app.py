"""Streamlit chat UI for the Northstar Commerce Business Data Assistant.

Talks to the FastAPI backend over HTTP (not by importing app.llm directly) so
the demo reflects the real UI -> API -> LLM -> tools -> Postgres architecture.
"""

from __future__ import annotations

import os

import requests
import streamlit as st

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Northstar Commerce Business Data Assistant", page_icon="📊")

st.title("📊 Northstar Commerce — Business Data Assistant")
st.caption(
    "Fictional portfolio demo. Northstar Commerce is not a real company; all "
    "data is synthetic. Answers come only from controlled database tools — "
    "the AI never invents business numbers."
)

with st.expander("Example questions"):
    st.markdown(
        "- What were our total sales in March?\n"
        "- Which products generated the most revenue?\n"
        "- Why did sales decrease in the second half of April?\n"
        "- Which customers had the highest number of failed transactions?\n"
        "- Compare revenue between January and February."
    )

question = st.text_input("Ask a question about Northstar Commerce's business data:")
ask_clicked = st.button("Ask", type="primary")

if ask_clicked and question.strip():
    with st.spinner("Thinking..."):
        try:
            response = requests.post(
                f"{API_BASE_URL}/ask", json={"question": question}, timeout=60
            )
        except requests.RequestException as exc:
            st.error(f"Could not reach the API at {API_BASE_URL}: {exc}")
            st.stop()

    if response.status_code == 503:
        st.warning(response.json().get("detail", "The assistant is not configured yet."))
    elif response.status_code >= 400:
        st.error(f"Request failed ({response.status_code}): {response.text}")
    else:
        data = response.json()
        st.markdown("### Answer")
        st.write(data["answer"])

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
