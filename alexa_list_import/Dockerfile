FROM python:3.12-alpine

RUN apk add --no-cache bash curl jq

# Python dependencies
RUN pip install --no-cache-dir \
    requests \
    pyyaml \
    flask \
    boto3

COPY run.sh /app/run.sh
COPY app.py /app/app.py

RUN chmod +x /app/run.sh

WORKDIR /app

CMD ["/app/run.sh"]
