# Use Python 3.9 slim base image
FROM python:3.9-slim

# Set maintainer label
LABEL maintainer="your-email@example.com"
LABEL description="Court Data Fetcher - Web scraping application for Indian court data"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies (including SQLite support)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    xsel \
    libnss3 \
    libgconf-2-4 \
    libxss1 \
    libayatana-appindicator1 \
    gconf-service \
    libasound2 \
    libatk1.0-0 \
    libc6 \
    libcairo-gobject2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgcc1 \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    ca-certificates \
    fonts-liberation \
    lsb-release \
    xdg-utils \
    sqlite3 \
    libsqlite3-dev \
 && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Create non-root user for security
RUN adduser --disabled-password --gecos '' --shell /bin/bash user \
    && chown -R user:user /app
USER user

# Copy requirements first for better caching
COPY --chown=user:user requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application code
COPY --chown=user:user . .

# Create necessary directories
RUN mkdir -p /app/logs /app/temp /app/downloads

# Set PATH to include user's pip binaries
ENV PATH="/home/user/.local/bin:${PATH}"

# Create startup script
RUN echo '#!/bin/bash\n\
# Initialize database\n\
python -c "from app import init_db; init_db()"\n\
\n\
# Start the application\n\
if [ "$FLASK_ENV" = "production" ]; then\n\
    exec gunicorn --bind 0.0.0.0:$PORT --workers 4 --timeout 120 app:app\n\
else\n\
    exec python app.py\n\
fi' > /app/start.sh && chmod +x /app/start.sh

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Set default environment variables
ENV PORT=5000
ENV HEADLESS_BROWSER=True
ENV DEBUG=False

# Run the application
CMD ["/app/start.sh"]
