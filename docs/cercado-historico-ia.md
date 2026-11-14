# Cercado, periurbanos, histórico e IA

Verificación: 12 de noviembre de 2026, hora de Bolivia.

## Estado

| Componente | Resultado |
|---|---|
| PostgreSQL/PostGIS | ✅ `db` healthy, persistencia activa y `/salud` HTTP 200. Solo este servicio está en Docker. |
| Cercado y distritos | ✅ Imagen real GAMC georreferenciada, visible por defecto. |
| Periurbanos | ✅ Imagen real GAMC visible, control independiente y foco NASA seleccionable por encima. |
| Disponibilidad GAMC | ⚠ La consulta actual agotó el tiempo de conexión. Se conservan imágenes recibidas con HTTP 200 el 10/11/2026 a las 21:01 BO. |
| Histórico 2025 | ✅ 45 registros MODIS en el área de observación; 5 elegibles, 32 de menor confianza y 8 descartados del análisis. |
| Gráficas e informes | ✅ Serie anual, frecuencia mensual, hora de adquisición, calendario, tabla de eventos, CSV, JSON e impresión a PDF. |
| IA local | ✅ Regresión Poisson entrenable bajo demanda y validación con un año separado. Solo 2025 no satisface la muestra mínima; no se inventa una predicción. |
| Regresiones | ✅ Foco NASA, orden de capas y controles conservados; pruebas PostGIS y de IA aprobadas. |
| Interfaz | ✅ Escritorio y móvil de 390 px sin desbordamiento horizontal. |

## Cartografía y alcance

La API documentada por [GAMC](https://recursosgamc.cochabamba.bo/api-doc) expone GetMap, GetLegendGraphic y GetFeatureInfo. Las respuestas guardadas son PNG de distritos y periurbanos, no geometrías vectoriales. La consulta de atributos guardada no incluía geometría.

Se recuperó del registro de la consulta original el bbox exacto `[-66.3,-17.55,-66.05,-17.25]`, EPSG:4326, 512 × 512. Las imágenes originales no fueron redibujadas. Fecha, identificadores de capas y SHA256 están en `data/geo/gamc/manifest.json`, sin claves. Ambas suman 141.004 bytes y se sirven con caché HTTP; mover el mapa no solicita nuevas teselas GAMC.

Las capas están en z-index 345; esquemas vectoriales en 350; focos y alertas en 400. Los esquemas ilustrativos anteriores se conservan como opción y se ocultan inicialmente. No se usan para clasificar oficialmente detecciones.

El filtro «Cercado» de los informes utiliza la extensión publicada para la capa GAMC, claramente rotulada como extensión cartográfica, no un polígono municipal exacto. En 2025 contiene 1 evento MODIS elegible. El informe inicial del entorno Cochabamba/Tunari contiene 5. Una imagen WMS no permite certificar distrito, proximidad al periurbano o pertenencia al PNT; sigue disponible la carga futura de GeoJSON verificados, incluidos Cercado y periurbanos.

## Informe 2025 del entorno

Fuente: [archivo anual MODIS NASA para Bolivia](https://firms.modaps.eosdis.nasa.gov/data/country/modis/2025/modis_2025_Bolivia.csv), publicado en el [catálogo NASA](https://firms.modaps.eosdis.nasa.gov/data/country/yearly_summary_files.txt).

| Indicador | Resultado |
|---|---:|
| Registros locales conservados | 45 |
| Eventos elegibles agrupados | 5 |
| Días con eventos elegibles | 4 |
| Días completos del archivo en hora Bolivia | 364 |
| Eventos por 30 días de archivo | 0,41 |
| Junio / septiembre / noviembre | 1 / 2 / 2 |

Se usa MODIS estándar con confianza >80 y sin fuentes descartadas. No se mezclan sensores de distinta resolución. Los eventos se agrupan en 1,5 km / 24 h; no equivalen a incendios confirmados. Las horas son de adquisición, no del inicio del fuego. La falta de registros o las nubes no prueban ausencia de fuego. El último día del archivo UTC no cubre las cuatro horas finales del día boliviano y se excluye del denominador completo.

2025 queda seleccionado por defecto. Antes de recibirse la preferencia por solo 2025 ya se habían importado 2021–2025: 42.061.853 bytes descargados una sola vez, 304 filas locales y 27.932 bytes conservados de CSV/metadatos. Se preservaron esos avances y no se descargaron más años. El paquete incluye únicamente el CSV local 2025 y su procedencia para reproducirlo sin red.

## IA y validación

Modelo local con cinco coeficientes: intercepto y dos armónicos de estacionalidad anual, regularización L2. No utiliza LLM externo, GPU, claves, librerías nuevas ni procesos persistentes. Las respuestas se guardan en caché cinco minutos y el entrenamiento se realiza bajo demanda.

Mínimo: tres años, 730 días de archivo completo y 20 eventos elegibles. Con 2025 la app muestra «Muestra insuficiente». El botón para analizar años ya guardados no hace descargas y solo aparece si existen al menos tres años completos importados.

Prueba con el entorno 2021–2025 ya guardado: 45 eventos elegibles. Entrenamiento 2021–2024; validación 2025 con 5 eventos. MAE modelo/base: **0,042 / 0,0405**; devianza modelo/base: **0,1307 / 0,1337**. La mejora de devianza es pequeña y el MAE empeora: no demuestra aptitud operativa. Las estimaciones de los siguientes 28 días son exploratorias de actividad MODIS, no probabilidades de incendio confirmado. No incluyen viento, lluvia, humedad ni combustible y no generan alertas automáticas.

Validación ejecutada: suite de 88 pruebas aprobada; después, dos pruebas de informes repetidas tras el ajuste de inventario y dos pruebas nuevas de conservación/actualización de la caché cartográfica aprobadas. Una advertencia preexistente de Starlette/httpx. Compilación Vite correcta, sin dependencias adicionales.

## Uso y reproducción

```powershell
curl.exe http://localhost:8000/salud
curl.exe http://localhost:8000/api/geografia/territorio
curl.exe "http://localhost:8000/api/informes/historico?desde=2025&hasta=2025&ambito=entorno"
# Desde backend, importar el archivo incluido sin descargarlo:
.\.venv\Scripts\python.exe scripts/cargar_historico.py ../data/historico/modis_2025_cochabamba.csv --source MODIS_SP --inicio 2025-01-01 --fin 2025-12-31 --completo
# Solo cuando se quiera renovar la cartografía, dos llamadas acotadas:
.\.venv\Scripts\python.exe scripts/actualizar_cartografia.py
```

Si GAMC falla, el actualizador conserva ambas imágenes anteriores y termina sin reintentos. No se ejecutó otra actualización del proveedor durante el cierre. Los datos operativos continúan en el volumen PostGIS existente; no se activaron nuevos workers ni descargas periódicas.

Al retomar el cierre, `db` estaba detenido: salida 0, `OOMKilled=false` y apagado solicitado a PostgreSQL, sin evidencia de pérdida de datos. Se recuperó únicamente con `docker compose up -d db`; no se recreó el volumen. Si se detiene manualmente, `restart: unless-stopped` respeta esa parada y hay que volver a iniciarlo.

Archivos principales: `app/services/informes.py`, `app/services/ia_incendios.py`, `app/services/cartografia.py`, rutas `informes.py`/`geografia.py`, scripts `descargar_historico.py`/`actualizar_cartografia.py`, `PanelEstadisticas.jsx`, `Mapa.jsx`, contexto, controles y estilos. Rutas de servicios bajo `backend/`, componentes bajo `frontend/src/`.

## Pendientes de datos

1. Renovar las imágenes cuando GAMC vuelva a responder; su caída es externa a PostGIS.
2. Incorporar límites vectoriales acreditados para atribuciones distritales y distancias precisas a periurbanos; los raster visibles no sustituyen esa geometría.
3. Para alertas predictivas operativas, ampliar y validar la muestra, incorporar meteorología y contrastar con incendios confirmados. El modelo actual permanece exploratorio.
