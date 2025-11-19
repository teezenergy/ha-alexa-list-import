FROM python:3.11-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY run.sh app.py ./
RUN chmod +x /app/run.sh

CMD ["/app/run.sh"]
