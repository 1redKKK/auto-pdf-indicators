# syntax=docker/dockerfile:1.7

# ─── Stage 1: build статического фронта Next.js ──────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /build

# Кешируемый слой с зависимостями
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Сам код
COPY frontend/ ./
RUN npm run build
# → /build/out/ содержит готовый статический фронт


# ─── Stage 2: runtime с FastAPI + WeasyPrint ─────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Linux-аналоги Windows GTK3 Runtime — нужны WeasyPrint для рендера PDF.
# fonts-dejavu-core — шрифты, которые используются в шаблоне monthly.html.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        libxml2 \
        libxslt1.1 \
        shared-mime-info \
        fonts-dejavu-core \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

# Python зависимости — отдельным слоем, чтобы изменения кода не инвалидировали cache
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

# Backend (включая pre-built moscow_3y.parquet, 1.4 MB)
COPY backend/ ./

# Static frontend из stage 1 — кладём так, чтобы относительный путь
# `<backend>/../frontend/out` из app/main.py разрешался корректно.
COPY --from=frontend-builder /build/out /app/frontend/out

# Storage для PDF отчётов и alerts_state — не персистентны без volume mount,
# но docker-compose монтирует тома, см. compose-файл.
RUN mkdir -p /app/backend/storage/reports

EXPOSE 8000

# Без --reload в проде. host=0.0.0.0 чтобы порт был виден снаружи контейнера.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
