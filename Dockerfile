# Multi-stage build for SRE Agent
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/services/sreagent/requirements.txt /build/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    kubectl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code - maintain directory structure
COPY backend /app/backend

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Set Python path to include /app
ENV PYTHONPATH=/app:${PYTHONPATH}

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
WORKDIR /app
CMD ["python", "-m", "uvicorn", "backend.services.sreagent.server:app", "--host", "0.0.0.0", "--port", "8000"]

