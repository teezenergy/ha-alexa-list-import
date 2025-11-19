FROM python:3.11-slim

# Arbeitsverzeichnis
WORKDIR /app

# System-Python Dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App Dateien
COPY app.py .
COPY run.sh .

# run.sh ausführbar machen
RUN chmod +x /app/run.sh

CMD [ "/app/run.sh" ]
