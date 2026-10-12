# Hugging Face Docker Space: FastAPI (internal :8000) + Streamlit (public :7860)
FROM python:3.11-slim
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH" API_BASE_URL=http://localhost:8000
WORKDIR /home/user/app
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=user app ./app
COPY --chown=user streamlit_app.py .
COPY --chown=user deploy/start.sh .
CMD ["bash", "start.sh"]
