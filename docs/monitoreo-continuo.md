# Monitoreo periódico mínimo — 13 de noviembre de 2026

## Plan aplicado y auditoría

Reutilizar el worker NRT, PostGIS y el Programador de tareas de Windows para un lote cada 3 horas. Mantener la consulta de la interfaz cada 60 segundos a la base local. No se agregaron contenedores, dependencias, streaming ni servicios externos.

| Componente existente | Situación encontrada | Decisión |
| --- | --- | --- |
| Worker `app.workers.ingesta_nrt` | Una ejecución manual; sin tarea periódica | Una tarea Windows, ejecución única cada 3 h |
| PostgreSQL/PostGIS | Disponible, con deduplicación y bloqueo de ingesta | Reutilizado; sin migración ni nueva tabla |
| Clientes NASA | CSV públicos sin MAP_KEY; cuatro productos configurados | Tres productos activos; reintentos limitados |
| Evaluador de anomalías | Sin geometrías verificadas ni evaluación vigente | Deshabilitado con motivo visible y bloqueo en el servicio |
| Bucle de monitoreo en memoria / `--loop` | Deshabilitado | Sigue deshabilitado |
| Notificaciones externas | Deshabilitadas | Siguen deshabilitadas; avisos de atraso en API/UI |
| GAMC y cachés cartográficas/históricas | Existentes | Conservados; se quitó la comprobación GAMC de cada ingesta NASA |

Las 3 h son una decisión de operación económica, no una garantía de detección instantánea. FIRMS indica disponibilidad global normalmente dentro de 3 h de la observación; el muestreo local añade hasta otro intervalo. [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/).

Suomi-NPP cesó su difusión operativa el 02/11/2026. Se retiró únicamente de las consultas NRT, conservando sus históricos y mostrando el motivo. [Estado oficial NOAA](https://star.nesdis.noaa.gov/icvs/status_NPP_sc.php), [aviso NASA/NSIDC](https://nsidc.org/data/user-resources/data-announcements/user-notice-s-nppvisible-infrared-imaging-radiometer-suite-viirs-data-sets-cessation-data-delivery).

## Cambios concretos

- `backend/scripts/programar_ingesta.ps1`: activa o desactiva una sola tarea, sin privilegios elevados ni contraseña guardada. Usa el entorno virtual existente y termina tras cada lote. No despierta el equipo.
- `firms_client.py`: dos reintentos como máximo, espera exponencial de 2/4 s, respeto de `Retry-After` numérico hasta 60 s; sin reintentar errores de credenciales ni CSV inválido. Tres descargas concurrentes como máximo y límite de 32 MiB por CSV público.
- `ingesta_nrt.py`: modo `--scheduled`, bloqueo exclusivo y deduplicación existentes, última ejecución programada/intento/éxito en `ingestas`. Intervalo persistido de 3 h; tolerancia de 60 s solo para el scheduler para evitar saltar un ciclo por demora de arranque. No se descarga el histórico.
- `monitoring_state.py`: estados continuo, atrasado, manual y sin dato; frescura por fuente; controles de geometría, configuración y evaluador reciente. Reutiliza la tabla `ingestas`.
- Estadísticas, API persistente y geografía: no se cambia `null` a cero. Un cero requiere fuentes activas vigentes; las observaciones positivas incompletas se indican como parciales. Alertas `null` mientras no haya evaluación válida.
- UI: última ingesta, próxima prevista, estado de fuentes, disponibilidad de indicadores y última comprobación/éxito del evaluador. Se conservan diseño, mapas, históricos e IA.
- Backend local consolidado en una instancia sin recargador; no se dejó un segundo worker residente.

## Configuración aplicada

En `.env` de la raíz, conservando las credenciales locales existentes:

```dotenv
DATABASE_ENABLED=true
LIVE_MONITORING_ENABLED=false
NRT_SCHEDULER_ENABLED=true
FIRMS_SOURCES=MODIS_NRT,VIIRS_NOAA20_NRT,VIIRS_NOAA21_NRT
NRT_INTERVAL_HOURS=3
NRT_DAYS=2
NRT_STALE_GRACE_MINUTES=20
NRT_SOURCE_MAX_AGE_HOURS=24
NRT_HTTP_RETRIES=2
NRT_MAX_DOWNLOAD_MB=32
ALERTS_EVALUATION_ENABLED=false
NOTIFICATIONS_ENABLED=false
```

Sin `FIRMS_MAP_KEY`, los CSV públicos cubren 24 h. `NRT_DAYS=2` se aplica solo al cliente de Área con clave. No se contrataron claves ni cuotas. `.env.example` deja el scheduler apagado para evitar activarlo al copiar el proyecto.

Una consulta queda atrasada después de 3 h + 20 min; además, un CSV público sin fecha de observación global válida o con observaciones de más de 24 h no habilita un cero. El evaluador debe tener geometrías verificadas, flag activo, fuentes vigentes y éxito posterior a la última ingesta, dentro del mismo margen. La lectura de la API no ejecuta evaluaciones.

## Comandos de activación y comprobación

Desde la raíz del proyecto, con el entorno existente:

```powershell
& .\backend\scripts\programar_ingesta.ps1
Get-ScheduledTask -TaskName 'Tunari Fire Monitor - Ingesta NRT'
Get-ScheduledTaskInfo -TaskName 'Tunari Fire Monitor - Ingesta NRT'
```

El script es idempotente respecto del nombre de tarea; volver a registrarla reprograma el primer disparo a un minuto. Ya está activada: no es necesario repetirlo. Tras cambiar `.env`, reiniciar únicamente la instancia FastAPI existente. Para un arranque posterior, en terminales separadas:

```powershell
docker compose up -d db
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
cd frontend
npm run dev
```

Verificación sin descargar datos:

```powershell
docker compose ps
curl.exe http://127.0.0.1:8000/salud
curl.exe http://127.0.0.1:8000/api/monitoreo?dias=1
curl.exe http://127.0.0.1:8000/api/estadisticas
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT COUNT(*) FROM detecciones_raw;"'
```

Para diagnóstico bajo demanda, desde `backend`: `.\.venv\Scripts\python.exe -m app.workers.ingesta_nrt --once`. Respeta el intervalo y no fuerza otra descarga reciente. No usar `--loop` junto a la tarea.

Desactivación reversible, desde la raíz: `& .\backend\scripts\programar_ingesta.ps1 -Desactivar`; después reiniciar FastAPI para recargar el flag. No elimina datos ni la tarea.

## Evidencia y aceptación

Horas de Bolivia (UTC−04), 13/11/2026. Se observó el primer disparo automático del Programador de tareas, sin ejecutar `Start-ScheduledTask` ni forzar el worker manualmente.

| Criterio | Resultado observado |
| --- | --- |
| Ingesta automática avanza | Cumple: pasó del 11/11 a 13/11, 19:17:01. Próximo disparo Windows: 22:16:38; repetición cada 3 h configurada. No se esperó un segundo intervalo completo. |
| Fuentes dejan de estar atrasadas | Cumple: MODIS, NOAA-20 y NOAA-21 vigentes. Últimas observaciones globales: 17:52, 15:36 y 16:21, respectivamente. |
| Diferenciar `null` y `0` | Cumple: `detecciones_hoy=0` con consulta válida sin detecciones en el bbox; `alertas_activas=null`. Cero detecciones no prueba ausencia de fuego. |
| Evaluador condicionado | Cumple: deshabilitado; 0/16 geometrías verificadas, ninguna ejecución exitosa. Última comprobación: 19:17:21. No se generaron alertas. |
| Estado visible | Cumple: «Monitoreo continuo», 3 productos vigentes, última ingesta, siguiente prevista y motivo del evaluador en la interfaz. |
| Recursos y costos | Cumple: una tarea local, el mismo PostGIS y backend, sin compras ni servicios de pago. |

El primer lote terminó con código **2 (parcial)** porque aún incluía Suomi-NPP, cuyo CSV tenía solo cabecera. Después se verificó el cese oficial y se corrigió el catálogo a las tres fuentes activas; todas habían terminado correctamente en ese lote. Se conservó el resultado original, sin falsificarlo ni repetir descargas. La API calcula la ingesta completa a partir de las fuentes actualmente configuradas; el control `worker:last_success` se registrará en el próximo lote completo con ese catálogo.

Las pruebas cubrieron `null`/cero/parcial, staleness, publicación congelada, backoff, geometrías y evaluación reciente. Suite completa: **103 aprobadas**; comprobaciones posteriores enfocadas: **23 y 22 aprobadas**. `npm run build` correcto. Navegador: indicadores y motivo visibles; sin errores ni mensajes de fallback a mocks. La salud de PostGIS respondió HTTP 200.

Para reproducir la suite PostGIS, desde `backend`, sin imprimir credenciales:

```powershell
.\.venv\Scripts\python.exe -c "import os, pytest; from app.config import get_settings; os.environ['TEST_DATABASE_URL']=get_settings().database_url; raise SystemExit(pytest.main(['-q']))"
```

Las pruebas de integración usan esquemas temporales propios; no borran los datos operativos.

## Registro, costo y límites

- Último reporte: `data/processed/ultima_ingesta_nrt.json`, reemplazo atómico; no acumulación de CSV ni logs verbose. Historial y controles en `ingestas`. Códigos de tarea: 0 correcto/omitido, 2 parcial/error de fuentes, 1 fallo de ejecución. Una tarea terminada no equivale por sí sola a datos vigentes.
- Máximo una ejecución concurrente, límite de 10 min, normalmente 3 solicitudes por lote; hasta 9 con reintentos. Se conservan bloqueos y cachés existentes. Los avisos de atraso son locales, sin correo/SMS de pago.
- **Costo adicional de API e infraestructura: US$0/mes.** Se reutilizan equipo, conexión y electricidad existentes; no se afirma que su consumo sea cero. El lote observado descargó aproximadamente 16,3 MB; a ocho lotes diarios serían unos 3,9 GB/mes si el volumen fuese similar, variable según actividad. No se activó IA externa ni GPU.
- Windows debe estar encendido, con la sesión del usuario abierta, acceso a Internet y Docker/PostGIS disponible. El job no necesita que el navegador esté abierto. Para consultar la app sí deben estar abiertos backend y frontend.
- La tarea usa `StartWhenAvailable`, no despierta el equipo y no ejecuta sin la sesión interactiva. No se promete disponibilidad 24/7 con un portátil apagado. Si deja de ejecutarse, los datos pasan a atrasados en la app; con el backend apagado tampoco puede mostrar nuevos avisos. [Opciones oficiales del Programador de tareas](https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtasksettingsset?view=windowsserver2025-ps).
- Una interrupción mayor de 24 h puede dejar huecos con los CSV públicos. No se completa el histórico automáticamente. La API de Área existente con clave gratuita permite limitar la descarga al bbox y usar 2 días, si posteriormente se configura.

## Pendientes: habilitar alertas en tres pasos

1. Obtener y documentar polígonos oficiales WGS84 de los 15 distritos y Tunari; sustituir los GeoJSON ilustrativos y validarlos. Las imágenes WMS de GAMC no cumplen este requisito.
2. Solo tras verificar su procedencia y precisión, cargar con `python scripts/cargar_geometrias.py --verificadas`, establecer `ALERTS_EVALUATION_ENABLED=true` y reiniciar FastAPI. No marcar como verificadas las geometrías actuales.
3. Con ingesta vigente, ejecutar `python -m app.workers.evaluador_anomalias`; comprobar `motor_alertas.disponible=true` y `ultima_exitosa` reciente. Si faltan datos de referencia para alguna unidad, conservar el motivo de indisponibilidad; nunca fabricar alertas. Los siguientes lotes reutilizarán el evaluador.
