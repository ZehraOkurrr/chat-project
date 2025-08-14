# ---- Build stage (opsiyonel ama temiz) ----
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Sistem bağımlılıkları (gerekirse ekleyebilirsin)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

# Gerekenler
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodu
COPY app/ app/
COPY domain/ domain/
COPY infrastructure/ infrastructure/
COPY static/ static/

# Prod için bazı env'ler
ENV PORT=8000 \
    TZ=Europe/Istanbul

EXPOSE 8000

# Uvicorn ile çalıştır
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
