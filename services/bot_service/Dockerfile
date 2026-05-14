FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy shared requirements first for better layer caching
COPY shared/requirements.txt ./shared_requirements.txt

# Copy service-specific requirements
COPY services/bot_service/requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY shared/ ./shared/

# Copy application code
COPY services/bot_service/ ./

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (bot service runs on 8002)
EXPOSE 8002

# Run application
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
