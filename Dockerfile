FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Chromium + chromedriver for Selenium tests in container.
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    ca-certificates \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Defaults for running against services on host machine (macOS/Windows Docker Desktop).
ENV BASE_URL=http://host.docker.internal:5173 \
    AUTH_URL=http://host.docker.internal:8000 \
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver \
    CHROME_HEADLESS=1

CMD ["pytest", "-v"]
