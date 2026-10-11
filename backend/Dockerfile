FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home app
COPY backend /app/backend
COPY frontend/src /app/frontend/src
COPY agents /app/agents
COPY scripts /app/scripts
COPY knowledge /app/knowledge
COPY shared /app/shared
COPY evals/cases /app/evals/cases
COPY evals/datasets /app/evals/datasets
RUN mkdir -p /app/evals/results && chown -R app:app /app/evals/results
USER app
ENV HOST=0.0.0.0
EXPOSE 8080
CMD ["python", "-m", "backend.app.api.server"]
