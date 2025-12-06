# Backend Dockerfile - Optimized for production
FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Copy requirements first for caching
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    "fastapi[standard]>=0.115.0" \
    "langchain>=0.3.0" \
    "langchain-core>=0.3.0" \
    "langchain-groq>=0.2.0" \
    "langchain-google-genai>=2.0.0" \
    "langgraph>=0.2.0" \
    "pydantic>=2.10.0" \
    "python-dotenv>=1.0.0" \
    "reportlab>=4.0.0" \
    "rich>=13.0.0" \
    "tavily-python>=0.5.0" \
    "uvicorn[standard]>=0.30.0" \
    "httpx>=0.27.0"

# Copy application code
COPY . .

# Create storage directory with proper permissions
RUN mkdir -p /app/storage && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Run the API - Use PORT env var for Render compatibility
CMD uvicorn api_v2:app --host 0.0.0.0 --port ${PORT:-8000}
