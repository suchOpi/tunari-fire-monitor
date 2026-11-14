# Tunari Fire Monitor
FastAPI + PostgreSQL/PostGIS + React/Vite. Logo personalizado; sin fallback a mocks.
Monitoreo periódico activado el 13/11/2026: una tarea Windows cada 3 h, tres fuentes NASA activas y PostGIS existente. Alertas deshabilitadas por falta de geometrías verificadas. [Plan, configuración, comandos, aceptación y costo](docs/monitoreo-continuo.md).
Los informes ya incluyen 2026 y los registros NRT, separados por sensor y con cobertura parcial explícita. [Gráficas, IA, verificación y meses pendientes de 2026](docs/informes-2026.md).
## Arranque local (PowerShell)
Desde esta carpeta, conserva `.env`; créalo desde `.env.example` solo si falta.
Credenciales `POSTGRES_*` y `DATABASE_URL` coherentes; host `localhost`, puerto `5432`.
Configura `DATABASE_ENABLED=true`, `LIVE_MONITORING_ENABLED=false` y `NRT_DAYS=2`.
Si Docker no está en PATH: `$env:Path = "$env:LOCALAPPDATA/Programs/DockerDesktop/resources/bin;$env:Path"`.
`docker compose up -d db`
`docker compose ps`: espera hasta 60 s a `healthy`, sin reiniciar el contenedor.
`cd backend` y `python -m venv .venv` (solo si aún no existe).
`./.venv/Scripts/python.exe -m pip install -r requirements.txt`
`./.venv/Scripts/python.exe scripts/cargar_geometrias.py`
`./.venv/Scripts/python.exe -m app.workers.ingesta_nrt` ejecuta un ciclo de ingesta real.
Sin MAP_KEY usa CSV NASA globales de 24 h filtrados al bbox; con clave usa exclusivamente la API de Área.
`./.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000` (una instancia, sin recargador).
En otra terminal, desde la raíz: `cd frontend`, `npm install`, `npm run dev`.
`frontend/.env`: `VITE_API_URL=/api`; Vite reenvía `/api` a `http://127.0.0.1:8000`.
Interfaz: http://localhost:5173. API: http://localhost:8000/docs.
## Recursos y persistencia
Compose contiene solo `db`, imagen `postgis/postgis:16-3.4`, reinicio `unless-stopped`.
Datos en el volumen nombrado `postgis_data`; los únicos bind-mounts son SQL de inicialización de solo lectura.
Puertos locales: 127.0.0.1:5432, 127.0.0.1:8000 y 127.0.0.1:5173.
Healthcheck `pg_isready` cada 10 s, `start_period: 30s`. Sin réplicas ni ajustes de PostgreSQL.
El mapa consulta registros PostGIS; GAMC es cartografía opcional con timeout de 5 s y pausa de 10 min tras un fallo.
Keyless consulta 24 h; la API de Área consulta NRT_DAYS. Intervalo persistido de 3 h; tarea `Tunari Fire Monitor - Ingesta NRT` activada, `--loop` apagado. Activación idempotente: `& ./backend/scripts/programar_ingesta.ps1`; requiere sesión Windows abierta y PostGIS disponible.
No se descargó el histórico 2000–2026 ni se activaron notificaciones externas.
`docker compose down` conserva el volumen. Conservarlo es necesario para mantener los registros.
## Pendientes
1. Obtener límites oficiales WGS84 de los 15 distritos y Tunari; reemplazar y documentar los GeoJSON. Las 16 geometrías actuales son ilustrativas: validez geométrica no equivale a verificación oficial.
2. Solo con esos límites comprobados, ejecutar `python scripts/cargar_geometrias.py --verificadas`, activar `ALERTS_EVALUATION_ENABLED=true` y reiniciar FastAPI.
3. Con fuentes vigentes, ejecutar `python -m app.workers.evaluador_anomalias` y comprobar éxito reciente en `/api/monitoreo`. Hasta entonces, las alertas permanecen `null` y se muestra el motivo.
MAP_KEY opcional: si se configura, el siguiente lote usa la API de Área. Los CSV sin `type` siguen requiriendo revisión; no se inventa clasificación de industria/volcán. Riesgos de suspensión del equipo y huecos de cobertura: [monitoreo continuo](docs/monitoreo-continuo.md).
GAMC 502 no bloquea los focos NASA. Diagnóstico: [docs/api_gamc.md](docs/api_gamc.md). Auditoría única: [docs/geometrias.md](docs/geometrias.md).
Incidencia resuelta: Docker no estaba en PATH; se usó su instalación por usuario y se abrió Docker Desktop. El error transitorio del motor desapareció al terminar su arranque.
## Verificación anterior (registro de puesta en marcha)
`curl.exe http://localhost:8000/salud` → HTTP 200, PostGIS 3.4, persistencia true.
`curl.exe http://localhost:8000/detecciones/recientes` → HTTP 200, 1 detección real VIIRS NOAA-21 con fuente=nasa_keyless.
`curl.exe http://localhost:8000/alertas` → array. `detecciones_raw`: 1 registro; posible_oclusion=false.
Pruebas: 88 casos superados, incluida integración PostGIS en esquemas temporales. `npm run build` correcto; ninguna dependencia nueva.
La interfaz muestra el foco y «Fuente: NASA FIRMS», sin fallback a mocks. Climatología y clasificación oficial siguen pendientes de sus datos respectivos.
Registro anterior: [docs/ingesta-keyless.md](docs/ingesta-keyless.md). La verificación vigente está en [docs/monitoreo-continuo.md](docs/monitoreo-continuo.md): ingesta automática del 13/11/2026, 103 pruebas aprobadas y cero detecciones observadas hoy con fuentes vigentes; alertas sin dato.
## Límites y distritos
`GET /geografia/distritos`: 15 polígonos y sus conteos; `GET /geografia/pnt`: polígono del parque.
`GET /geografia/distrito/{id}`: geometría y estadísticas bajo demanda; también disponibles bajo `/api/geografia/*`.
Los toggles «Mostrar límites de distritos» y «Mostrar Parque Nacional Tunari» controlan las capas locales.
Las tarjetas seleccionan, filtran y centran; «Todos los distritos» restaura la vista general.
Geometrías en caché y una carga por montaje; tras reemplazarlas, reinicia el backend y recarga la página.
Los límites actuales son ilustrativos; población ausente se muestra «Sin dato».
Validación y archivos modificados: [docs/mejora-mapa.md](docs/mejora-mapa.md).
## Cercado, informes 2025 e IA local
Distritos y periurbanos GAMC visibles desde imágenes originales guardadas, con fecha y bbox en `data/geo/gamc/manifest.json`; no se descargan teselas al mover el mapa.
Los esquemas vectoriales ilustrativos quedan opcionales; las imágenes WMS no habilitan clasificación espacial oficial de focos.
Informes, gráficas anual/mensual/horaria, calendario, CSV y JSON: `/api/informes/historico?desde=2025&hasta=2025&ambito=entorno`.
IA Poisson local bajo demanda, caché 5 min y validación temporal; sin claves, dependencias nuevas, GPU ni workers adicionales.
La selección inicial es año anterior–año actual (2025–2026 hoy). Con datos insuficientes no hay predicción; los años ya importados pueden consultarse sin descarga. El seguimiento NRT del año actual no completa por sí solo los meses anteriores.
Para reproducir 2025 sin red: desde `backend`, `./.venv/Scripts/python.exe scripts/cargar_historico.py ../data/historico/modis_2025_cochabamba.csv --source MODIS_SP --inicio 2025-01-01 --fin 2025-12-31 --completo`.
Diagnóstico, alcance y verificaciones: [docs/cercado-historico-ia.md](docs/cercado-historico-ia.md).
