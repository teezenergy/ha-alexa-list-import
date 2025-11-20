ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM $BUILD_FROM

# Install basic OS packages
RUN apk update && apk add --no-cache \
    python3 \
    py3-pip \
    python3-venv \
    jq \
    curl

# Create app folder
RUN mkdir -p /app
WORKDIR /app

# Create a virtual environment for Python
RUN python3 -m venv /app/venv

# Ensure pip inside venv is up-to-date
RUN /app/venv/bin/pip install --upgrade pip

# Copy files
COPY requirements.txt .
COPY app.py .
COPY run.sh .

# Install app requirements in venv
RUN /app/venv/bin/pip install --no-cache-dir -r requirements.txt

# Make start script executable
RUN chmod +x /app/run.sh

# Add-on startup command
CMD ["/app/run.sh"]
