# ==============================================================================
# Knowvia AI — FastAPI Backend Dockerfile (CPU Optimized for Cloud & ECS)
# ==============================================================================
FROM python:3.10-slim

# Prevent Python from writing .pyc files and enable unbuffered logging with UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV TQDM_DISABLE=1
ENV HF_HUB_DISABLE_SYMLINKS_WARNING=1
ENV TRANSFORMERS_VERBOSITY=error
ENV PYTHONWARNINGS=ignore
ENV HOST=0.0.0.0
ENV PORT=8000

WORKDIR /app

# Install basic build tools and curl for health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install CPU-optimized PyTorch first for fast layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir torch --extra-index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend code, data, and configuration
COPY backend/ ./backend/
COPY data/ ./data/

# Expose backend service port
EXPOSE 8000

# Health check for Docker / AWS container lifecycle
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Launch FastAPI backend with Uvicorn
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
