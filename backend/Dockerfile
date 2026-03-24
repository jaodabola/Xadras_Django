# Build stage
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random

# Set work directory
WORKDIR /usr/src/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt python-json-logger

# Copy project
COPY . .

# Create and set permissions for static and media directories
RUN mkdir -p /usr/src/app/staticfiles /usr/src/app/media \
    && chmod -R 755 /usr/src/app/staticfiles /usr/src/app/media

# Final stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random

# Set work directory
WORKDIR /usr/src/app

# Install system dependencies for runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Create and set permissions for static and media directories
RUN mkdir -p /usr/src/app/staticfiles /usr/src/app/media \
    && chmod -R 755 /usr/src/app/staticfiles /usr/src/app/media

# Copy from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/src/app /usr/src/app

# Set the working directory to where manage.py is located
WORKDIR /usr/src/app/xadras

# Ensure all directories exist and have correct permissions before collecting static files
RUN mkdir -p /usr/src/app/static /usr/src/app/staticfiles /usr/src/app/media /usr/src/app/xadras/static \
    && chmod -R 755 /usr/src/app/static /usr/src/app/staticfiles /usr/src/app/media /usr/src/app/xadras/static

# Collect static files
RUN python manage.py collectstatic --noinput --clear

# Expose the port the app runs on
EXPOSE 8000

# Create a separate Python script for checking database using HEREDOC for better readability
RUN { \
    echo 'import os'; \
    echo 'import sys'; \
    echo 'import psycopg2'; \
    echo 'import time'; \
    echo ''; \
    echo 'max_retries = 30'; \
    echo 'retry_delay = 2'; \
    echo ''; \
    echo 'for i in range(max_retries):'; \
    echo '    try:'; \
    echo '        conn = psycopg2.connect('; \
    echo '            dbname=os.environ["POSTGRES_DB"],'; \
    echo '            user=os.environ["POSTGRES_USER"],'; \
    echo '            password=os.environ["POSTGRES_PASSWORD"],'; \
    echo '            host="db",'; \
    echo '            connect_timeout=2'; \
    echo '        )'; \
    echo '        conn.close()'; \
    echo '        print("Database is ready!")'; \
    echo '        sys.exit(0)'; \
    echo '    except Exception as e:'; \
    echo '        print(f"Waiting for database... (Attempt {i+1}/{max_retries}) {e}")'; \
    echo '        if i == max_retries - 1:'; \
    echo '            print("Max retries reached. Exiting.")'; \
    echo '            sys.exit(1)'; \
    echo '        time.sleep(retry_delay)'; \
} > /usr/local/bin/wait_for_db.py

# Create a simple entrypoint script using HEREDOC for better readability
RUN { \
    echo '#!/bin/sh'; \
    echo 'set -e'; \
    echo ''; \
    echo '# Create required directories if they don\'\''t exist'; \
    echo 'mkdir -p /usr/src/app/static /usr/src/app/staticfiles /usr/src/app/media /usr/src/app/xadras/static'; \
    echo 'chmod -R 755 /usr/src/app/static /usr/src/app/staticfiles /usr/src/app/media /usr/src/app/xadras/static'; \
    echo ''; \
    echo '# Wait for database'; \
    echo 'echo "Waiting for database..."'; \
    echo 'python3 /usr/local/bin/wait_for_db.py'; \
    echo ''; \
    echo '# Run migrations'; \
    echo 'python manage.py migrate --noinput'; \
    echo ''; \
    echo '# Collect static files with clear flag to avoid conflicts'; \
    echo 'python manage.py collectstatic --noinput --clear'; \
    echo ''; \
    echo '# Start Daphne ASGI server for WebSocket support'; \
    echo 'exec python -m daphne -b 0.0.0.0 -p 8000 xadras.asgi:application'; \
} > /usr/local/bin/entrypoint.sh && \
    chmod +x /usr/local/bin/entrypoint.sh && \
    dos2unix /usr/local/bin/entrypoint.sh

# Install production-only Python dependencies
RUN pip install --no-cache-dir gunicorn==21.2.0 whitenoise==6.6.0 daphne==4.1.2

# Verify installations
RUN python -c "import daphne; print('Daphne installed successfully')"

# Command to run the application
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["python", "-m", "daphne", "-b", "0.0.0.0", "-p", "8000", "xadras.asgi:application"]