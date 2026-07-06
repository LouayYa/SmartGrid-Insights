# syntax=docker/dockerfile:1

# ---------- Stage 1: builder — installs deps into an isolated venv ----------
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt

# ---------- Stage 2: runtime — slim image with only the venv + app code ----------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

# Copies the app code AND the household_power_consumption.csv dataset the
# ingestion endpoints read at runtime (kept out of .dockerignore on purpose).
COPY . .

RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
