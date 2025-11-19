FROM python:3.11-slim

# System-Pakete für jq / pip
RUN apt-get update && \
    apt-get install -y jq && \
    apt-get clean

# Arbeitsverzeichnis
WORKDIR /app

# Python Requirements
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# App & run.sh
COPY run.sh /app/run.sh
COPY app.py /app/app.py

# run.sh ausführbar machen
RUN chmod +x /app/run.sh

CMD [ "/app/run.sh" ]
