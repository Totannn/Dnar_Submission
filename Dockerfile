# Multi-stage build for production fintech application
# Security is critical for Dnar's regulated environment

FROM python:3.11-slim as builder

WORKDIR /build

# Install dependencies in virtual environment
COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ============================================
# Final production image
# ============================================
FROM python:3.11-slim

# Metadata labels for compliance
LABEL maintainer="ml-ops-team@dnar.io" \
      version="1.0.0" \
      description="Transaction Risk Scoring Service" \
      compliance="AML/KYC compliant" \
      security-scan="required"

# Create non-root user (security best practice)
RUN useradd -m -u 1000 -s /bin/bash mlops && \
    mkdir -p /app/models && \
    chown -R mlops:mlops /app

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=mlops:mlops main.py .
COPY --chown=mlops:mlops train_model.py .

# Switch to non-root user (CRITICAL for security)
USER mlops

# Environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    MODEL_PATH="/app/models/model.pkl" \
    MODEL_VERSION="v1.0.0" \
    ENVIRONMENT="production" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Health check (fintech SLA: service must respond within 5s)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
# For production: use multiple workers for high availability
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]