# Claude Code Orchestration System - Production Dockerfile
# Multi-stage build for optimized image size

FROM python:3.11-slim AS base

# Set working directory
WORKDIR /app

# Install system dependencies (minimal)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy source code
COPY src/ ./src/
COPY config/ ./config/
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/sessions /app/logs

# Set Python path
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "from src.config_loader import load_config; load_config()" || exit 1

# Default command (can be overridden)
CMD ["python3", "-m", "src.config_loader", "--help"]

# Production stage (smaller image)
FROM python:3.11-slim AS production

WORKDIR /app

# Copy only necessary files from base
COPY --from=base /app /app
COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Set environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run as non-root user
RUN useradd -m -u 1000 claude && \
    chown -R claude:claude /app
USER claude

CMD ["python3", "-m", "src.config_loader", "--help"]
