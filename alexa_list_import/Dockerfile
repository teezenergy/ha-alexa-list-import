FROM python:3.12-alpine

WORKDIR /app

RUN apk add --no-cache bash curl jq

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY run.sh /app/run.sh
RUN chmod +x /app/run.sh

COPY app.py /app/app.py

CMD ["/app/run.sh"]
