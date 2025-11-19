FROM python:3.12-alpine

RUN apk add --no-cache bash jq py3-yaml

WORKDIR /app

COPY app.py /app/app.py
COPY run.sh /app/run.sh

RUN chmod +x /app/run.sh

CMD ["/app/run.sh"]
