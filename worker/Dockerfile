FROM python:3.13.5-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ffmpeg \
       fonts-noto-cjk \
       fonts-noto-color-emoji \
       tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY worker/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY worker/app ./app
COPY index.html manifest.webmanifest service-worker.js ./static/
COPY assets ./static/assets
RUN useradd --create-home --uid 10001 worker \
    && mkdir -p /data \
    && chown -R worker:worker /app /data

USER worker
EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips=*", "--no-server-header"]
