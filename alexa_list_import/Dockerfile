ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

RUN apk add --no-cache python3 py3-pip bash
RUN pip3 install requests pyyaml

WORKDIR /app
COPY run.sh /app/run.sh
COPY app.py /app/app.py

RUN chmod +x /app/run.sh

CMD ["/app/run.sh"]
