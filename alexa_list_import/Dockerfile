FROM python:3.12-alpine

RUN apk add --no-cache bash curl jq

WORKDIR /app
COPY run.sh app.py /app/

RUN chmod +x /app/run.sh

CMD ["/app/run.sh"]
