# syntax=docker/dockerfile:1.7
# Multi-stage Dockerfile for NotebookLM MCP CLI

# Stage 1: Builder with uv package manager
FROM python:3.12-slim AS builder
WORKDIR /app

# Install uv and build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files and README (required by pyproject.toml)
COPY pyproject.toml uv.lock* README.md ./

# Copy source for full install
COPY src/ src/

# Build virtual environment with project (frozen lock ensures reproducibility)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# Stage 2: Development
FROM python:3.12-slim AS development
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy venv from builder
COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy source code
COPY . .

# Install the package in development mode
RUN pip install -e .

# Create non-root user
RUN useradd -m -u 1001 appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://127.0.0.1:8080/health || exit 0

CMD ["notebooklm-mcp"]

# Stage 3: Production
FROM python:3.12-slim AS production
WORKDIR /app

LABEL org.opencontainers.image.title="notebooklm-mcp" \
      org.opencontainers.image.description="NotebookLM MCP Server" \
      org.opencontainers.image.version="1.0" \
      org.opencontainers.image.vendor="Production"

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    dumb-init \
    && rm -rf /var/lib/apt/lists/*

# Copy venv from builder
COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONOPTIMIZE=2

# Copy source and pyproject (needed by installed package)
COPY src/ src/
COPY pyproject.toml ./

# Create non-root user
RUN useradd -m -u 1001 appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://127.0.0.1:8080/health || exit 0

ENTRYPOINT ["dumb-init", "--"]
CMD ["notebooklm-mcp"]
