ARG BUILD_FROM=ghcr.io/hassio-addons/base/ubuntu:latest
FROM ${BUILD_FROM}

# Install dependencies
RUN apt-get update && \
    apt-get install -y python3 python3-pip jq curl && \
    pip3 install --no-cache-dir -r /app/requirements.txt

# Copy all files
COPY run.sh /app/run.sh
COPY app.py /app/app.py
COPY requirements.txt /app/requirements.txt

RUN chmod +x /app/run.sh

CMD [ "/app/run.sh" ]
