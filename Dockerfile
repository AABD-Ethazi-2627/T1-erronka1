# Python-en irudi ofiziala (arina)
FROM python:3.10-slim

# Python-ek .pyc fitxategiak idaztea ekiditen du eta stdout/stderr buffer gabe uzten ditu
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Lan-direktorioa edukiontziaren barruan
WORKDIR /app

# Sistemako beharrezko mendekotasunak instalatu (curl healthcheck-erako)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Beharren fitxategia kopiatu eta instalatu
COPY scoring/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Iturburu-kodea kopiatu (eredua ./models-etik bolumen bidez muntatzen da).
# cnc_ml beharrezkoa da: .pkl-ak bere feature engineering funtzioak erreferentziatzen ditu.
COPY scoring/app ./app
COPY scoring/cnc_ml ./cnc_ml
RUN mkdir -p /models
ENV MODEL_PATH=/models/cnc_failure_model.pkl

# FastAPI-ren portua kanporatu
EXPOSE 8000

# Uvicorn bidez APIa abiarazteko komandoa
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
