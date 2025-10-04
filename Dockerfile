# syntax = docker/dockerfile:1
FROM python:3.13-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements_agno.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements_agno.txt && \
    pip install --no-cache-dir fastapi "uvicorn[standard]" python-dotenv

# Copy only what we need
COPY fastapi_server.py .
COPY agno_bridge_v2.py .
COPY evidence_coordinator_full.py .
COPY audit_logger.py .
COPY alpine_frontend.html .
COPY .env .
COPY scripts/* .
COPY public/* .
EXPOSE 8080

# Healthcheck hits /health
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8080/health || exit 1

# Run uvicorn in the foreground on the correct port
CMD ["python","-m","uvicorn","fastapi_server:app","--host","0.0.0.0","--port","8080","--proxy-headers"]
