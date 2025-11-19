ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# Install Python + pip
RUN apk add --no-cache python3 py3-pip bash

# Install Python modules
RUN pip3 install requests pyyaml

# Create app dir
WORKDIR /app

COPY run.sh /app/run.sh
COPY app.py /app/app.py

RUN chmod +x /app/run.sh

CMD ["/app/run.sh"]
