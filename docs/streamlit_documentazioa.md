# 🛠️ NEXO CNC — Panel Streamlit

Aplicación web interactiva desarrollada con **Streamlit** para la monitorización en tiempo real del estado de las máquinas CNC, visualización de métricas de telemetría, gestión de alertas y simulación manual de predicciones.

---

## 📌 Funcionalidades y Vistas

La aplicación se compone de 4 secciones accesibles desde la barra lateral:

### 1. 📊 Dashboard (Estado de las máquinas)
* **KPIs globales**: Total de máquinas monitorizadas, número de alertas activas, riesgo medio estimado de la flota y temperatura ambiental.
* **Lista priorizada de máquinas**: Ordenadas de mayor a menor riesgo de avería según la última predicción.
* **Detalle por máquina**: Al seleccionar un equipo, muestra:
  * Gráficas temporales interactivas (desgaste de herramienta, par motor, temperaturas).
  * Rangos estables de trabajo frente a los valores actuales.
  * Relación entre par y desgaste (`wear_torque`) y salto térmico (`temp_diff_K`).

### 2. ⚡ Predicción Manual (Simulador)
* Formulario interactivo para introducir parámetros operativos de una máquina:
  * Tipo de máquina (`L`, `M`, `H`)
  * Temperatura ambiente y del proceso (K)
  * Velocidad rotacional (RPM)
  * Par de torsión (Nm)
  * Desgaste de herramienta (min)
* Calcula en tiempo real la probabilidad de fallo y el nivel de alerta correspondiente consultando la Scoring API.

### 3. 🔍 Explorador de Datos
* Tabla interactiva con el historial de predicciones y telemetría.
* Filtros por nivel de alerta (`OK`, `KONTUZ`, `LARRIA`) y ventana de tiempo.
* Visualización detallada de registros individuales en formato tabular.

### 4. 🚨 Centro de Alertas
* Vista enfocada en incidencias activas clasificadas en:
  * 🟡 **KONTUZ** (Riesgo medio / desgaste preventivo)
  * 🔴 **LARRIA** (Riesgo crítico / parada recomendada)
* Historial de eventos anómalos para el equipo de mantenimiento.

---

## 🔌 Orígenes de Datos

La aplicación de Streamlit obtiene su información de dos servicios:

| Origen | Endpoint por defecto | Uso en la aplicación |
|---|---|---|
| **Elasticsearch** | `http://elasticsearch:9200` | Consulta de índices para el Dashboard, gráficas, tablas y alertas: <br>• `cnc-predictions` (predicciones y niveles de alerta)<br>• `cnc-sensors` (telemetría directa de sensores) |
| **Scoring API** | `http://scoring-api:8000` | • `GET /health`: Estado del modelo ML en la barra lateral.<br>• `POST /predict`: Inferencia en tiempo real del formulario manual. |

---

## ⚙️ Variables de Entorno

Configurables en el entorno o archivo `.env`:

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `ES_URL` | `http://elasticsearch:9200` | Dirección del servidor Elasticsearch |
| `ES_INDEX` | `cnc-predictions` | Índice de predicciones de fallo |
| `ES_SENSOR_INDEX` | `cnc-sensors` | Índice de lecturas de sensores |
| `API_URL` | `http://scoring-api:8000` | Dirección de la API de inferencia FastAPI |
| `API_USERNAME` | `nifi` | Usuario para autenticación en la API |
| `API_PASSWORD` | *(vacío)* | Contraseña para autenticación en la API |

---

## 🚀 Puesta en Marcha

### Con Docker Compose

```bash
# Iniciar únicamente el contenedor de Streamlit
docker compose -f docker-compose.dev.yml up -d streamlit
```
Acceso en el navegador: **`http://localhost:8501`**

### En Local (sin Docker)

```bash
# 1. Instalar dependencias
pip install -r streamlit/requirements.txt

# 2. Configurar variables (si difieren de las por defecto)
export ES_URL="http://localhost:9200"
export API_URL="http://localhost:8000"
export API_PASSWORD="tu_password"

# 3. Lanzar Streamlit
streamlit run streamlit/app.py
```

---

## 🎨 Características Adicionales

* **Tema Claro / Oscuro**: Selector de tema en la barra lateral con persistencia durante la sesión.
* **Congelar Datos (Instantánea)**: Botón para pausar la actualización automática de datos y permitir el análisis estático de un incidente sin que se muevan los gráficos.
* **Caché Eficiente**: Uso de `@st.cache_data` con tiempos de expiración controlados para evitar sobrecargar Elasticsearch.

---

## 📁 Estructura del Módulo

```text
streamlit/
├── app.py              # Entrada principal, router de navegación y vistas
├── config.py           # Lectura de variables de entorno y constantes
├── requirements.txt    # Librerías necesarias (streamlit, requests, altair, pandas...)
├── Dockerfile          # Imagen para el despliegue en contenedor
├── ui/
│   ├── __init__.py
│   └── theme.py        # Control de estilos CSS y temas claro/oscuro
└── README.md           # Esta documentación
```
