# XADRAS Vision Service - Raspberry Pi 5 Dockerfile
# For running on Raspberry Pi with AI Camera

FROM python:3.11-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create models directory if not exists
RUN mkdir -p /app/models

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV USE_PICAMERA=false
ENV CAMERA_INDEX=0
ENV BACKEND_WS_URL=ws://localhost:8000/ws/vision/
ENV DEBUG=false

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "print('OK')" || exit 1

# Run the service
CMD ["python", "main.py"]
