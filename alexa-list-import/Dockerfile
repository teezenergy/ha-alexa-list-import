ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM $BUILD_FROM

# Install system packages (Alpine)
RUN apk update && apk add --no-cache \
    python3 \
    py3-pip \
    py3-virtualenv \
    jq \
    curl \
    chromium \
    chromium-chromedriver \
    ttf-freefont \
    bash \
    build-base

# Create app dir
RUN mkdir -p /app
WORKDIR /app

# Copy files
COPY requirements.txt /app/requirements.txt
COPY run.sh /app/run.sh
COPY app.py /app/app.py

# make the run script executable
RUN chmod +x /app/run.sh

# create venv and install python deps inside venv
RUN python3 -m virtualenv /app/venv
RUN /app/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

# Ensure webdriver is available in PATH (chromedriver from apk is in /usr/bin)
ENV PATH="/usr/bin:${PATH}"
ENV HOME=/root

CMD [ "/app/run.sh" ]
