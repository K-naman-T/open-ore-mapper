FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir --user '.[api,emit]'

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libblas3 \
    liblapack3 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY src/ /app/src/
COPY examples/ /app/examples/
WORKDIR /app

ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

EXPOSE 8000

CMD ["uvicorn", "open_ore_mapper.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
