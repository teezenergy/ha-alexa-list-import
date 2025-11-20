ARG BUILD_FROM=ghcr.io/hassio-addons/base:12.2.8
FROM ${BUILD_FROM}

# Install dependencies (Alpine Linux → apk)
RUN apk update && \
    apk add --no-cache python3 py3-pip jq curl

# Create /app directory
RUN mkdir -p /app

# Copy files
COPY requirements.txt /app/requirements.txt
COPY app.py /app/app.py
COPY run.sh /app/run.sh

# Python dependencies
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# Permissions
RUN chmod +x /app/run.sh

CMD [ "/app/run.sh" ]
