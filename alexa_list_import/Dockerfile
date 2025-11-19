FROM python:3.12-alpine

# Install system dependencies
RUN apk add --no-cache bash jq py3-yaml

# Create app directory
WORKDIR /app

# Copy files
COPY app.py /app/app.py
COPY run.sh /app/run.sh

# Ensure run.sh is executable
RUN chmod +x /app/run.sh

CMD ["/app/run.sh"]
