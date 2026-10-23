# Estructura de la aplicación Streamlit

La aplicación mantiene `app.py` como punto de entrada para no romper el
despliegue actual (`streamlit run app.py`) y separa las responsabilidades
reutilizables en módulos:

```text
streamlit/
├── app.py                 # Entrada, router y composición de páginas
├── config.py              # Variables de entorno y constantes
├── ui/
│   ├── __init__.py
│   └── theme.py           # Tema claro/oscuro y componentes visuales
├── pages/                 # Reservado para extraer cada vista en módulos
├── services/              # Reservado para API, Elasticsearch y Telegram
└── requirements.txt
```

El selector de apariencia está en la barra lateral y se conserva durante la
sesión. El modo oscuro es el valor predeterminado.
