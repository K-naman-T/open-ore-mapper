FROM python:3.12-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY data/ ./data/
RUN pip install --no-cache-dir --target /opt/spectral-deps '.[api]'

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libblas3 liblapack3 && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home spectral
COPY --from=builder /opt/spectral-deps /opt/spectral-deps
COPY src/ /app/src/
COPY data/ /app/data/
COPY examples/ /app/examples/
RUN chown -R spectral:spectral /app /opt/spectral-deps
USER spectral
WORKDIR /app
ENV PYTHONPATH=/app/src:/opt/spectral-deps PYTHONUNBUFFERED=1 MPLBACKEND=Agg
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "spectral_matching.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
