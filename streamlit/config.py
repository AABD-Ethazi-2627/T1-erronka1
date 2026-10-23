"""Configuración central de la aplicación Streamlit."""

import os


API_URL = os.getenv("API_URL", "http://scoring-api:8000").rstrip("/")
API_USERNAME = os.getenv("API_USERNAME", "nifi")
API_PASSWORD = os.getenv("API_PASSWORD", "")
ES_URL = os.getenv("ES_URL", "http://elasticsearch:9200").rstrip("/")
ES_INDEX = os.getenv("ES_INDEX", "cnc-predictions")

MAILAK = ["OK", "KONTUZ", "LARRIA"]
