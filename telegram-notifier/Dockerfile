FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
RUN pip install --no-cache-dir requests==2.32.3
COPY notifier.py .

CMD ["python", "notifier.py"]
