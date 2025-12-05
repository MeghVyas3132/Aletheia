# Backend Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi>=0.122.0 \
    langchain>=0.3.0 \
    langchain-core>=0.3.0 \
    langchain-groq>=0.2.0 \
    langgraph>=0.2.0 \
    pydantic>=2.12.5 \
    python-dotenv>=1.2.1 \
    reportlab>=4.4.5 \
    rich>=14.2.0 \
    tavily-python>=0.5.0 \
    uvicorn>=0.38.0

# Copy application code
COPY . .

# Create storage directory
RUN mkdir -p /app/storage

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "api_simple:app", "--host", "0.0.0.0", "--port", "8000"]
