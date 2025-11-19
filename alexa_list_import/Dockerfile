FROM python:3.11-slim

WORKDIR /app

# Install system packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends jq && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app.py .
COPY run.sh .

# Ensure run.sh is executable
RUN chmod +x /app/run.sh

CMD [ "/app/run.sh" ]
