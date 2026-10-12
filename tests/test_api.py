"""FastAPI endpoint tests using TestClient — no live server, DB, or API key needed."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.main import app
from app.llm.models import AssistantResponse, ToolCallRecord

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ask_returns_503_when_openai_key_missing(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_FALLBACK_BASE_URL", raising=False)
    monkeypatch.setattr("app.llm.client._providers", None)
    monkeypatch.setattr("app.llm.client._env_loaded", True)
    response = client.post("/ask", json={"question": "What were sales in March?"})
    assert response.status_code == 503
    assert "LLM_API_KEY" in response.json()["detail"]


def test_ask_rejects_empty_question():
    response = client.post("/ask", json={"question": "   "})
    assert response.status_code == 400


def test_ask_returns_mocked_assistant_response():
    fake_response = AssistantResponse(
        question="What were sales in March?",
        answer="Total revenue in March was $120,000.",
        tool_calls=[
            ToolCallRecord(
                tool_name="get_sales_summary",
                arguments={"start_date": "2024-03-01", "end_date": "2024-03-31"},
                result={"total_revenue": 120000.0, "order_count": 500, "avg_order_value": 240.0},
            )
        ],
    )
    with patch("app.api.main.answer_question", return_value=fake_response) as mock_answer:
        response = client.post("/ask", json={"question": "What were sales in March?"})

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Total revenue in March was $120,000."
    assert data["tool_calls"][0]["tool_name"] == "get_sales_summary"
    mock_answer.assert_called_once_with("What were sales in March?")
