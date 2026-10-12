"""FastAPI backend: exposes the LLM tool-calling assistant over HTTP."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.llm.assistant import answer_question
from app.llm.models import AssistantResponse

app = FastAPI(
    title="Northstar Goods — Payment Loss Assistant API",
    description="Fictional portfolio demo: a small online store losing money to payment failures, refunds and chargebacks. Synthetic data only.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ask", response_model=AssistantResponse)
def ask(payload: AskRequest):
    question = payload.question.strip()
    if not question:
        return JSONResponse(status_code=400, content={"detail": "question must not be empty."})

    try:
        return answer_question(question)
    except RuntimeError as exc:
        # Raised by app.llm.client / app.database.connection when
        # LLM_API_KEY / DATABASE_URL are missing — a configuration
        # problem, not a client error, so 503 rather than 500/400.
        return JSONResponse(status_code=503, content={"detail": str(exc)})
