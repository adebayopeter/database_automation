# Multi-stage build for Database Automation Suite
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VERSION=2.0.0
ARG VCS_REF

# Set labels for metadata
LABEL maintainer="Database Automation Team <db-automation@company.com>" \
      version="${VERSION}" \
      description="Database Automation Suite for PostgreSQL and SQL Server" \
      build-date="${BUILD_DATE}" \
      vcs-ref="${VCS_REF}"

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP_USER=automation \
    APP_GROUP=automation \
    APP_HOME=/app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r ${APP_GROUP} && \
    useradd -r -g ${APP_GROUP} -d ${APP_HOME} -s /bin/bash ${APP_USER}

# Create directories
RUN mkdir -p ${APP_HOME}/logs ${APP_HOME}/reports ${APP_HOME}/backups && \
    chown -R ${APP_USER}:${APP_GROUP} ${APP_HOME}

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Set working directory
WORKDIR ${APP_HOME}

# Copy application files
COPY --chown=${APP_USER}:${APP_GROUP} database_automation.py .
COPY --chown=${APP_USER}:${APP_GROUP} db_config.yaml .
COPY --chown=${APP_USER}:${APP_GROUP} .env.example .env
COPY --chown=${APP_USER}:${APP_GROUP} requirements.txt .

# Create health check script
RUN echo '#!/bin/bash\npython database_automation.py status > /dev/null 2>&1' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh && \
    chown ${APP_USER}:${APP_GROUP} /app/healthcheck.sh

# Switch to non-root user
USER ${APP_USER}

# Expose ports
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /app/healthcheck.sh

# Use tini as init system
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command
CMD ["python", "database_automation.py", "monitor", "--metrics-port", "8000"]