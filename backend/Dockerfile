FROM python:3.11-slim AS base
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ── production ───────────────────────────────────────────────────────────────
FROM base AS production
RUN adduser --disabled-password --gecos "" appuser
USER appuser
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

# ── test ─────────────────────────────────────────────────────────────────────
FROM base AS test
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
CMD ["sh", "-c", "alembic upgrade head && python -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-fail-under=85"]
