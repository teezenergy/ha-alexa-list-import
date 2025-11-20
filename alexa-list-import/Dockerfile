ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM $BUILD_FROM

# Install packages
RUN apk update && apk add --no-cache \
    python3 \
    py3-pip \
    py3-virtualenv \
    jq \
    curl

# Create app directory
RUN mkdir -p /app

# Copy app files
COPY requirements.txt /app/requirements.txt
COPY app.py /app/app.py
COPY run.sh /app/run.sh

# Create virtual environment
RUN python3 -m venv /app/venv

# Install Python dependencies in venv
RUN /app/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

# Make run.sh executable
RUN chmod +x /app/run.sh

CMD ["/app/run.sh"]
