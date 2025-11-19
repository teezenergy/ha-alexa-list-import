FROM python:3.11-slim

# Update system + install jq
RUN apt-get update && \
    apt-get install -y jq && \
    apt-get clean

# Copy files
COPY run.sh /app/run.sh
COPY app.py /app/app.py
COPY requirements.txt /app/requirements.txt

# Install python libs
RUN pip install --no-cache-dir -r /app/requirements.txt

# Make script executable
RUN chmod +x /app/run.sh

WORKDIR /app

CMD ["/app/run.sh"]
