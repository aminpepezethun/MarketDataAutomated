FROM python:3.10-slim

WORKDIR /usr/src/app

# Install dependencies for Playwright Chromium
RUN apt-get update && apt-get install -y wget curl gnupg libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxss1 libx11-xcb1 libxcomposite1 libxrandr2 libgtk-3-0 libgbm1 libasound2 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

COPY . .

CMD ["python", "./logic.py"]

