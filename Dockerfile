FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 WEB_DIR=/app/web TZ=UTC
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install ".[dev]"
COPY web ./web
COPY tests ./tests
RUN useradd -r -u 10001 app && mkdir -p /data/raw_archive && chown -R app /data
USER app
