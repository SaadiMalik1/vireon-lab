# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain nightly
ENV PATH="/root/.cargo/bin:${PATH}"

RUN pip install --no-cache-dir --upgrade pip maturin build

COPY pyproject.toml README.md ./
COPY neuro_dsl ./neuro_dsl
COPY vireon ./vireon

RUN python -m build --wheel

# Stage 2: Final runtime image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7777

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl[all] && rm -rf /tmp/*.whl

RUN groupadd -r vireon && useradd -r -g vireon -d /app vireon && \
    chown -R vireon:vireon /app

USER vireon

EXPOSE 7777

CMD ["python", "-m", "vireon", "ui", "--port", "7777", "--host", "0.0.0.0"]
