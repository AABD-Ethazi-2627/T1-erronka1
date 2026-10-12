FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY score_api.py .

RUN mkdir -p /models

ENV MODEL_PATH=/models/cnc_failure_model.pkl

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "score_api:app", "--host", "0.0.0.0", "--port", "8000"]
