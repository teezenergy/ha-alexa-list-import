ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM $BUILD_FROM

# Set shell
SHELL ["/bin/ash", "-eo", "pipefail", "-c"]

# Install required Alpine packages
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-virtualenv \
    jq \
    curl

# Create app directory
RUN mkdir -p /app

# Copy application files
COPY app.py /app/app.py
COPY run.sh /app/run.sh
COPY requirements.txt /app/requirements.txt

# Make run.sh executable
RUN chmod +x /app/run.sh

# Create Python virtual environment
RUN python3 -m venv /app/venv \
 && /app/venv/bin/pip install --upgrade pip \
 && /app/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

# Default command
CMD [ "/app/run.sh" ]
