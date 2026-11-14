# Tunari Fire Monitor

Tunari Fire Monitor ayuda a consultar y revisar focos de calor detectados por satélites en el entorno del Parque Nacional Tunari y Cochabamba. Muestra los registros en un mapa y permite consultar informes históricos. **Un foco de calor es una señal que podría estar relacionada con un incendio; no confirma por sí solo que haya fuego.**

El proyecto está construido con FastAPI, PostgreSQL/PostGIS y React/Vite. La interfaz usa el logo personalizado y no sustituye los datos reales por ejemplos simulados.

## Estado del monitoreo y de los datos

- El monitoreo automático se activó el 13/11/2026. En Windows, una tarea revisa nuevas detecciones cada 3 horas y utiliza tres fuentes de NASA. La base de datos geográfica PostGIS ya está disponible.
- Las alertas automáticas están desactivadas porque todavía no se han confirmado oficialmente los límites geográficos de los distritos y del parque. Las formas que se muestran hoy son ilustrativas, no límites oficiales.
- Los informes incluyen datos de 2026 y registros recientes, separados por sensor. Se indica claramente cuando la información de un período está incompleta. Consulta [gráficas, IA, verificaciones y meses pendientes de 2026](docs/informes-2026.md).
- La verificación registrada el 13/11/2026 encontró una ingesta automática activa, 103 pruebas aprobadas y ninguna detección observada ese día con las fuentes vigentes. Esto describe esa revisión, no garantiza que siempre haya datos nuevos. Más detalles en [monitoreo continuo](docs/monitoreo-continuo.md).

## Cómo iniciar el proyecto en tu computadora (Windows)

Estos pasos se realizan en PowerShell. Necesitas Docker Desktop, Python y Node.js instalados. La aplicación tiene dos partes: un servicio que obtiene y entrega los datos, y una página web que los muestra.

1. Abre PowerShell en la carpeta del proyecto. Conserva el archivo `.env` si ya existe; créalo a partir de `.env.example` solo si falta.
2. En `.env`, asegúrate de que los datos de conexión `POSTGRES_*` coincidan con `DATABASE_URL`. La conexión local usa `localhost` y el puerto `5432`. Configura también:

   ```env
   DATABASE_ENABLED=true
   LIVE_MONITORING_ENABLED=false
   NRT_DAYS=2
   ```

3. Si PowerShell no encuentra Docker, agrega su carpeta al PATH de esta sesión:

   ```powershell
   $env:Path = "$env:LOCALAPPDATA/Programs/DockerDesktop/resources/bin;$env:Path"
   ```

4. Inicia la base de datos:

   ```powershell
   docker compose up -d db
   ```

   Comprueba que esté lista con `docker compose ps`. Espera hasta 60 segundos a que su estado sea `healthy`; no reinicies el contenedor mientras termina de arrancar.

5. Prepara el servicio de datos. Entra en `backend` y crea el entorno de Python solo si todavía no existe:

   ```powershell
   cd backend
   python -m venv .venv
   ./.venv/Scripts/python.exe -m pip install -r requirements.txt
   ./.venv/Scripts/python.exe scripts/cargar_geometrias.py
   ```

6. Si quieres ejecutar una revisión manual de los datos disponibles, ejecuta un ciclo de ingesta:

   ```powershell
   ./.venv/Scripts/python.exe -m app.workers.ingesta_nrt
   ```

   Sin `MAP_KEY`, se consultan archivos CSV globales de NASA de las últimas 24 horas y se filtran para el área del mapa. Con `MAP_KEY`, se utiliza únicamente la API de Área.

7. Inicia el servicio API en una sola instancia y sin recarga automática:

   ```powershell
   ./.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

8. Abre otra terminal en la carpeta principal del proyecto e inicia la página web:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

   En `frontend/.env`, configura `VITE_API_URL=/api`. Vite reenvía las solicitudes `/api` al servicio en `http://127.0.0.1:8000`.

- Página web: http://localhost:5173
- Documentación de la API: http://localhost:8000/docs

## Datos guardados y servicios

- Docker Compose inicia únicamente la base de datos `db`, usando la imagen `postgis/postgis:16-3.4`. Si se detiene, Docker la inicia de nuevo (`unless-stopped`).
- Los registros se guardan en el volumen `postgis_data`. `docker compose down` detiene los servicios, pero conserva ese volumen. **No lo borres si quieres conservar los registros.** Los únicos archivos del proyecto conectados directamente al contenedor son archivos SQL de inicialización, montados como solo lectura.
- Los servicios se limitan a tu computadora: base de datos en `127.0.0.1:5432`, API en `127.0.0.1:8000` y página web en `127.0.0.1:5173`.
- Docker comprueba cada 10 segundos si la base de datos responde y le da 30 segundos iniciales para arrancar. No se configuran copias adicionales de la base ni ajustes especiales de PostgreSQL.
- El mapa usa los registros guardados en PostGIS. El mapa de GAMC es opcional: si falla, espera 5 segundos como máximo y vuelve a intentar después de 10 minutos.
- La consulta sin clave (`keyless`) busca las últimas 24 horas. La API de Área consulta el período indicado por `NRT_DAYS`. La tarea de Windows `Tunari Fire Monitor - Ingesta NRT` está activada cada 3 horas; `--loop` permanece apagado. Para activarla de forma segura si todavía no está programada, desde la raíz ejecuta:

  ```powershell
  & ./backend/scripts/programar_ingesta.ps1
  ```

  Para que la tarea funcione, Windows debe estar abierto y PostGIS disponible.
- No se descargó el conjunto histórico de 2000 a 2026 ni se activaron avisos externos.

## Qué falta y qué significan las alertas

1. Conseguir límites oficiales en formato WGS84 para los 15 distritos y el Parque Nacional Tunari, y reemplazar y documentar los archivos GeoJSON actuales. Las 16 formas existentes son ilustrativas: que un archivo tenga una forma válida no significa que sus límites estén confirmados oficialmente.
2. **Solo después de comprobar esos límites**, cargar las formas verificadas con `python scripts/cargar_geometrias.py --verificadas`, activar `ALERTS_EVALUATION_ENABLED=true` y reiniciar FastAPI.
3. Con las fuentes de datos vigentes, ejecutar `python -m app.workers.evaluador_anomalias` y confirmar que `/api/monitoreo` muestre una ejecución reciente exitosa. Hasta entonces, las alertas aparecen como `null` (sin resultado), junto con el motivo.

`MAP_KEY` es opcional. Si se configura, la siguiente consulta usa la API de Área. Los archivos CSV que no incluyen el campo `type` requieren revisión: el sistema no inventa si un foco es de origen industrial o volcánico. Puede haber interrupciones del equipo o períodos sin datos; consulta el [registro de monitoreo continuo](docs/monitoreo-continuo.md).

Un error 502 de GAMC no impide mostrar los focos de NASA. Para conocer el diagnóstico, consulta [la API de GAMC](docs/api_gamc.md) y la [revisión de las formas geográficas](docs/geometrias.md).

Incidencia ya resuelta durante la puesta en marcha: Docker no estaba disponible en el PATH. Se localizó la instalación del usuario y se abrió Docker Desktop; el error temporal desapareció al terminar el arranque.

## Comprobaciones registradas

La siguiente información corresponde a una verificación anterior, no a una comprobación en tiempo real:

- `curl.exe http://localhost:8000/salud` respondió HTTP 200; PostGIS 3.4 y la persistencia de datos estaban disponibles.
- `curl.exe http://localhost:8000/detecciones/recientes` respondió HTTP 200 y devolvió una detección real VIIRS NOAA-21, recibida mediante `nasa_keyless`.
- `curl.exe http://localhost:8000/alertas` devolvió una lista. Se registró una detección sin procesar (`detecciones_raw`) y `posible_oclusion=false`.
- Pasaron 88 pruebas, incluidas pruebas de integración con PostGIS en esquemas temporales. `npm run build` terminó correctamente y no se añadieron dependencias.
- La página mostró el foco con «Fuente: NASA FIRMS», sin reemplazarlo por datos simulados. Aún faltan los datos necesarios para la climatología y la clasificación oficial.

El registro previo está en [ingesta sin clave](docs/ingesta-keyless.md). Para el estado y las comprobaciones más recientes, consulta [monitoreo continuo](docs/monitoreo-continuo.md).

## Mapa, límites y distritos

El mapa puede mostrar los 15 distritos y el Parque Nacional Tunari. Los límites actuales son ilustrativos y la población que no está disponible aparece como «Sin dato».

- Los controles «Mostrar límites de distritos» y «Mostrar Parque Nacional Tunari» permiten mostrar u ocultar esas formas.
- Las tarjetas de distrito permiten elegir uno, filtrar sus datos y centrar el mapa. «Todos los distritos» vuelve a la vista general.
- Las formas se guardan temporalmente en caché y se cargan una vez al abrir la página. Si se reemplazan los archivos, reinicia el servicio y recarga la página.
- La API ofrece `GET /geografia/distritos` (formas y conteos), `GET /geografia/pnt` (forma del parque) y `GET /geografia/distrito/{id}` (forma y estadísticas del distrito solicitado). También están disponibles bajo `/api/geografia/*`.

Consulta [la validación del mapa y los archivos modificados](docs/mejora-mapa.md).

## Cercado, informes históricos e IA

- Los distritos y las zonas periurbanas de GAMC se muestran a partir de imágenes originales guardadas. La fecha y el área cubierta se anotan en `data/geo/gamc/manifest.json`. No se descargan imágenes nuevas al mover el mapa.
- Algunas formas dibujadas son ilustrativas y opcionales. Las imágenes WMS sirven como referencia visual, pero no permiten confirmar oficialmente en qué zona ocurrió un foco.
- Los informes ofrecen gráficas anuales, mensuales y por hora, calendario y descarga en CSV o JSON. Por ejemplo, este enlace consulta el entorno de 2025: `/api/informes/historico?desde=2025&hasta=2025&ambito=entorno`.
- La función de IA usa un cálculo estadístico local basado en Poisson y se ejecuta cuando se solicita. Guarda el resultado durante 5 minutos y comprueba su validez frente a datos anteriores. No necesita claves, nuevas dependencias, GPU ni procesos adicionales en segundo plano.
- Al abrir los informes se selecciona el año anterior y el actual (2025–2026 en la configuración registrada). Si no hay datos suficientes, no se genera una predicción. Los años cuyos datos ya se importaron se pueden consultar sin descargar nada. El seguimiento reciente (NRT) del año actual no incluye todos los meses anteriores.
- Para volver a cargar el archivo histórico de 2025 sin conexión a internet, desde `backend` ejecuta:

  ```powershell
  ./.venv/Scripts/python.exe scripts/cargar_historico.py ../data/historico/modis_2025_cochabamba.csv --source MODIS_SP --inicio 2025-01-01 --fin 2025-12-31 --completo
  ```

Consulta [el diagnóstico, alcance y verificaciones](docs/cercado-historico-ia.md).
