# Documentación de la aplicación Streamlit

## 1. Descripción

La aplicación Streamlit proporciona el panel web de **CNC Guard**, una
plataforma de mantenimiento predictivo para máquinas CNC.

Desde el panel se puede:

- Consultar el estado de la API de predicciones.
- Consultar el estado de Elasticsearch.
- Visualizar métricas de disponibilidad y riesgo.
- Explorar predicciones históricas.
- Ejecutar predicciones manuales.
- Consultar y filtrar alertas de mantenimiento.
- Cambiar el tema visual y configurar la actualización automática.

El punto de entrada es `app.py`.

## 2. Estructura del proyecto

```text
streamlit/
├── app.py                    # Entrada de la aplicación
├── config.py                 # Variables de entorno y constantes
├── core/                     # Arranque y navegación
│   └── application.py
├── views/                    # Pantallas de la aplicación
│   ├── dashboard.py
│   ├── predicciones.py
│   ├── datos.py
│   └── alertas.py
├── services/                 # Integraciones y datos
│   ├── scoring.py
│   ├── elasticsearch.py
│   ├── data.py
│   ├── http.py
│   └── exceptions.py
├── ui/                       # Tema, CSS, iconos y gráficos
│   ├── charts.py
│   ├── icons.py
│   ├── theme.py
│   └── styles.css
├── Dockerfile
├── requirements.txt
└── .dockerignore
```

`views` se utiliza en lugar de `pages` porque `pages` es un nombre reservado
por el sistema multipágina automático de Streamlit.

| Módulo | Responsabilidad |
|---|---|
| `app.py` | Punto de entrada estable para Docker y Streamlit. |
| `core/` | Configuración, navegación y ciclo de ejecución. |
| `views/` | Interfaz y flujo de usuario de cada pantalla. |
| `services/` | API de scoring, Elasticsearch y transformación de datos. |
| `ui/` | Tema, estilos, iconos y gráficos reutilizables. |
| `config.py` | Configuración basada en variables de entorno. |

## 3. Requisitos

- Python 3.10 o superior.
- Streamlit 1.40.2.
- API de scoring disponible.
- Elasticsearch disponible para consultar datos históricos.

Las dependencias están fijadas en `requirements.txt`.

## 4. Ejecución local

Desde la carpeta `streamlit/`:

```bash
python -m venv .venv
```

Activación en Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instalación y arranque:

```bash
pip install -r requirements.txt
streamlit run app.py
```

La aplicación estará disponible en `http://localhost:8501`.

## 5. Ejecución con Docker Compose

Desde la raíz del proyecto:

```bash
docker compose up -d --build streamlit
```

Comprobar el estado:

```bash
docker compose ps streamlit
```

Consultar logs:

```bash
docker logs cnc-streamlit --tail 100
```

El servicio expone el puerto `8501` y utiliza este healthcheck:

```text
http://localhost:8501/_stcore/health
```

## 6. Configuración

La aplicación utiliza las siguientes variables de entorno:

| Variable | Valor predeterminado | Descripción |
|---|---|---|
| `API_URL` | `http://scoring-api:8000` | URL de la API de scoring. |
| `API_USERNAME` | `nifi` | Usuario de autenticación. |
| `API_PASSWORD` | vacío | Contraseña de autenticación. |
| `ES_URL` | `http://elasticsearch:9200` | URL de Elasticsearch. |
| `ES_INDEX` | `cnc-predictions` | Índice de predicciones. |

Ejemplo para PowerShell:

```powershell
$env:API_URL = "http://localhost:8000"
$env:API_USERNAME = "nifi"
$env:API_PASSWORD = "tu contraseña"
$env:ES_URL = "http://localhost:9200"
$env:ES_INDEX = "cnc-predictions"
streamlit run app.py
```

## 7. Flujo de ejecución

```text
app.py
  ↓
core.application.main()
  ↓
configure_app()
  ↓
render_sidebar()
  ↓
views.<pantalla>.render()
  ↓
services y ui
```

`app.py` no contiene lógica de negocio. Solo importa y ejecuta `main()`.

## 8. Pantallas

### Dashboard

Implementado en `views/dashboard.py`. Muestra:

- Máquinas detectadas.
- Disponibilidad estimada.
- Alertas activas.
- MTBF calculado con el histórico disponible.
- Distribución de niveles de alerta.
- Evolución del riesgo.
- Máquinas con mayor probabilidad de fallo.

Los datos se obtienen de Elasticsearch mediante
`services.elasticsearch.dashboard_documents()`.

### Predicciones

Implementado en `views/predicciones.py`. Permite enviar a la API:

- Identificador de máquina.
- Tipo de carga.
- Temperatura del aire.
- Temperatura del proceso.
- Revoluciones por minuto.
- Par motor.
- Desgaste de herramienta.

La comunicación se realiza mediante `services.scoring.predict()`.

### Datos

Implementado en `views/datos.py`. Permite filtrar por nivel de alerta, número
de registros e identificador de máquina. Los resultados se convierten a un
`pandas.DataFrame` mediante `services.data.load_predictions()`.

### Alertas

Implementado en `views/alertas.py`. Permite filtrar por máquina, periodo y
nivel de alerta. Los niveles disponibles son `OK`, `KONTUZ` y `LARRIA`.

## 9. Servicios externos

### API de scoring

`services/scoring.py` se encarga de:

1. Solicitar tokens en `/auth/token`.
2. Guardar el token temporalmente en `st.session_state`.
3. Reutilizar el token mientras siga siendo válido.
4. Reintentar una predicción si la API responde con `401`.
5. Comprobar el estado de la API mediante `/health`.

### Elasticsearch

`services/elasticsearch.py` se encarga de ejecutar búsquedas, consultar
conteos, cargar datos del dashboard y gestionar las cachés de Streamlit.

Las excepciones específicas se definen en `services/exceptions.py`:

- `ElasticsearchUnavailable`: el servicio no responde.
- `ElasticsearchIndexMissing`: el índice todavía no existe.

## 10. Caché y actualización

Las consultas utilizan `st.cache_data` para evitar peticiones innecesarias:

- Estado de la API: 10 segundos.
- Conteos de Elasticsearch: 15 segundos.
- Documentos y dashboard: 10 segundos.

Los botones de actualización manual llaman a
`services.elasticsearch.clear_cache()` y fuerzan un nuevo renderizado.

La barra lateral permite actualizar automáticamente cada 30 segundos, 1, 10 o
30 minutos, 1 hora, o desactivar la actualización.

## 11. Estilos y gráficos

Los estilos globales se encuentran en `ui/styles.css` y se cargan dentro de
una etiqueta `<style>` desde `core/application.py`.

El tema visual está gestionado por `ui/theme.py` y se conserva en
`st.session_state`.

Los gráficos compartidos están definidos en `ui/charts.py`, que centraliza
colores, fondos, ejes y estilos para los modos claro y oscuro.

## 12. Añadir una nueva pantalla

1. Crear un archivo en `views/`, por ejemplo `mantenimiento.py`.
2. Definir una función pública `render()`.
3. Importar el módulo en `core/application.py`.
4. Añadirlo al diccionario `PAGES`.

Ejemplo:

```python
# views/mantenimiento.py
import streamlit as st


def render() -> None:
    st.title("Mantenimiento")
```

Registro:

```python
from views import mantenimiento

PAGES = {
    "Mantenimiento": mantenimiento.render,
}
```

## 13. Buenas prácticas

- No realizar peticiones HTTP directamente desde las vistas.
- Mantener las consultas a Elasticsearch dentro de `services/`.
- No guardar secretos en el código fuente.
- Usar variables de entorno para las credenciales.
- Reutilizar componentes de `ui/` antes de crear estilos nuevos.
- Mantener una función `render()` por vista.
- Limpiar las cachés después de cambios manuales en los datos.
- Ejecutar `git diff --check` antes de hacer commit.
- Reconstruir Docker después de cambiar dependencias o archivos copiados.

## 14. Problemas frecuentes

### La API aparece como Offline

Comprobar que `scoring-api` está arrancado, que `API_URL` es correcto y que las
credenciales están configuradas.

### Elasticsearch aparece como Offline

Comprobar que Elasticsearch está arrancado, que `ES_URL` es correcto y que el
contenedor Streamlit puede acceder a él por la red Docker.

### No aparecen datos

El índice puede existir pero estar vacío. Comprobar que el flujo de NiFi está
activo y que está enviando documentos a `cnc-predictions`.

### La interfaz aparece sin estilos

Comprobar que `ui/styles.css` existe y que se carga dentro de
`<style>...</style>`. Después reconstruir el contenedor:

```bash
docker compose up -d --build streamlit
```

## 15. Comprobaciones antes de entregar cambios

Desde la raíz del proyecto:

```bash
git diff --check
docker compose config --quiet
```

Si Docker está iniciado:

```bash
docker compose up -d --build streamlit
docker compose ps streamlit
```
