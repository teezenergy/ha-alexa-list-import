FROM python:3.11-alpine

# benötigte Pakete installieren
RUN apk add --no-cache bash jq py3-yaml

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true

COPY run.sh app.py ./
RUN chmod +x /app/run.sh

CMD ["/app/run.sh"]
