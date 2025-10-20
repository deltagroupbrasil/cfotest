# ===============================================
# Multi-stage Dockerfile for Delta CFO Agent
# Optimized for Google Cloud Run with PostgreSQL
# ===============================================

# Stage 1: Build dependencies
FROM python:3.11-slim as builder

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    g++ \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create build environment
WORKDIR /build
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime image
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    tesseract-ocr \
    tesseract-ocr-por \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/app/.local

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/web_ui/classified_transactions /app/web_ui/uploads /app/logs && \
    chown -R app:app /app

# Switch to non-root user
USER app

# Add local Python packages to PATH
ENV PATH=/home/app/.local/bin:$PATH

# Set environment variables for Cloud Run
ENV PYTHONPATH=/app
ENV FLASK_APP=web_ui/app_db.py
ENV PORT=8080
ENV DB_TYPE=postgresql

# Cloud SQL environment variables (will be set by Cloud Run)
ENV DB_HOST=""
ENV DB_PORT=5432
ENV DB_NAME=delta_cfo
ENV DB_USER=""
ENV DB_PASSWORD=""
ENV DB_SOCKET_PATH=""

# Application environment variables
ENV ANTHROPIC_API_KEY=""
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Health check using Python instead of curl
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:$PORT/health').getcode()" || exit 1

# Expose port
EXPOSE 8080

# Start command optimized for Cloud Run
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 --max-requests 1000 --max-requests-jitter 100 --preload web_ui.app_db:app