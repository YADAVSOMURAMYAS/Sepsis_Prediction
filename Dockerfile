# ── Stage 1: build dependencies ───────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# gcc/g++ for XGBoost; libpq-dev for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: lean runtime image ───────────────────────────────────────────────
FROM python:3.11-slim

# libpq is needed at runtime by psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installed packages from builder
COPY --from=builder /install /usr/local

# Backend source code
COPY backend/ .

# XGBoost model — ml_model.py resolves to /Sepsis-Prediction/xgboost_model.pkl
COPY Sepsis-Prediction/xgboost_model.pkl /Sepsis-Prediction/xgboost_model.pkl

# Cloud Run sets PORT (default 8080)
ENV PORT=8080

EXPOSE 8080

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
