# Use Python slim image for smaller footprint
FROM python:3.9-slim

# Add non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    PIP_NO_CACHE_DIR=1

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies and clean up in one layer to reduce image size
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -rf /root/.cache/pip/*

# Copy application code
COPY . .

# Set correct permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user for security
USER appuser

# Optional EXPOSE instruction (Cloud Run ignores this)
EXPOSE ${PORT}

# Healthcheck configuration
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl --fail http://localhost:${PORT}/health || exit 1

# Use JSON format for CMD as recommended by Cloud Run
CMD ["gunicorn", "--bind", ":8080", "--workers", "1", "--threads", "8", "--timeout", "0", "main:app"]