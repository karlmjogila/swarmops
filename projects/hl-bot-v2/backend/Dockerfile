# ===== Build Stage =====
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies to system python (no virtualenv)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root --only main

# ===== Production Stage =====
FROM python:3.11-slim AS production

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser -g 1001 && \
    useradd -r -g appuser -u 1001 -m -s /bin/bash appuser && \
    mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ===== Development Stage =====
FROM builder AS development

WORKDIR /app

# Install dev dependencies
RUN poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /app/data /app/logs

EXPOSE 8000

# Development with auto-reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
