ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM $BUILD_FROM

# Install system packages
RUN apk update && apk add --no-cache \
    python3 \
    py3-pip \
    py3-virtualenv \
    jq \
    curl

# Create app directory
RUN mkdir -p /app

# Copy files
COPY app.py /app/app.py
COPY run.sh /app/run.sh
COPY requirements.txt /app/requirements.txt

# Make run.sh executable
RUN chmod +x /app/run.sh

# Create venv and install Python deps
RUN python3 -m venv /app/venv
RUN /app/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

CMD [ "/app/run.sh" ]
