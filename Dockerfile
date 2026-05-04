FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for crawl4ai / playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl gnupg libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    libxshmfence1 libx11-xcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright browsers for crawl4ai
RUN python -m playwright install chromium

COPY . .

CMD ["python", "worker_html.py"]
