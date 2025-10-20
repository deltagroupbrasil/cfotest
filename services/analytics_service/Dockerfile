FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements for analytics service
COPY services/analytics_service/requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy analytics service code
COPY services/analytics_service/ ./services/analytics_service/

# Copy shared dependencies (database will be created if not exists)
RUN mkdir -p ./web_ui

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_APP=services.analytics_service.app:app
ENV PORT=8080
ENV DATABASE_PATH=/app/web_ui/delta_transactions.db

# Create necessary directories
RUN mkdir -p /app/logs

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/analytics/status || exit 1

# Run the Flask app
CMD ["python", "-m", "services.analytics_service.app"]