# Arquitectura

**Actualización de integración real:** la interfaz ahora consume `/api/monitoreo` y WMS GAMC, sin fallback a mock. La configuración local sin PostGIS es un monitor de lectura; el flujo persistente descrito abajo se conserva como módulo independiente. Véase `integracion-real.md` para fuentes, endpoints y verificación actual.

NRT/CSV → normalización → detecciones_raw → agrupación PostGIS → eventos_incendio → evaluación semanal → alertas → API → mapa.
PostGIS almacena WGS84; distancia geodésica en metros y malla UTM EPSG:32719 de 1 km. `hex_id` identifica celdas regulares, no hexágonos H3.

## Ejecución y persistencia

- Docker Compose separa API, worker y base; el frontend Nginx es un perfil opcional. Todos los puertos publicados están vinculados a 127.0.0.1.
- `.env` raíz es común; `backend/.env` puede sobrescribirla en ejecución local. No guardar credenciales en frontend.
- La API crea tablas al iniciar. `scripts/crear_tablas.sql` es la alternativa SQL equivalente, para instalación nueva; no es un sistema de migraciones.
- El worker usa un bloqueo PostgreSQL y un último intento persistido: reiniciarlo o duplicarlo no adelanta la siguiente consulta de 3 h.
- Cada fuente se confirma en una transacción independiente. Un error conserva registros previos y se registra como error, nunca como ausencia de fuego.
- Importar un CSV es transaccional; un error de fila revierte el archivo completo. La huella del archivo evita recargarlo; la clave de detección también evita duplicados entre archivos y ventanas.
- El raw original se conserva como JSON, además de las columnas normalizadas. Una observación estándar reemplaza los atributos NRT equivalentes; no ocurre a la inversa.
- Sin MAP_KEY el worker no llama a NASA. Las notificaciones están deshabilitadas por defecto. No se incluyen archivos históricos reales.

## API propia

| Ruta | Uso |
|---|---|
| GET `/api/salud` | Estado PostGIS y presencia de clave, sin exponer secretos |
| GET `/api/detecciones` | Detecciones no descartadas; incluye candidatas |
| GET `/api/eventos` | Eventos que intersectan el intervalo |
| GET `/api/alertas` | Alertas; filtro opcional `estado` |
| PATCH `/api/alertas/{id}` | Estado nueva/en_revision/atendida/falsa_alarma |
| POST `/api/alertas/{id}/confirmar` | Revisión manual confirmada; habilita notificación si procede |
| GET `/api/estadisticas` | KPIs, serie por año, cobertura y estado de fuentes |
| GET `/geo/{archivo}.geojson` | Geometrías del directorio compartido |

Consultas: `dias=1..366`, `distrito=1..15`, `desde=YYYY-MM-DD`, `hasta=YYYY-MM-DD`. Fechas inclusivas en America/La_Paz. Un día significa día civil, no ventana móvil. Las listas devuelven `items`, `total`, `truncado`; el límite se informa en pantalla. Reducir intervalo si se supera. Los endpoints son de la aplicación; el único endpoint de datos NASA usado es el de Área documentado.

El cliente actual solicita un conjunto coherente a `/api/monitoreo`. Si falla, muestra el error y conserva únicamente una consulta real anterior identificada como tal; sin consulta previa deja los indicadores sin datos. Nunca carga mocks. Reintenta cada minuto y permite actualizar manualmente, respetando la caché de descarga de 3 h. El mapa consume WMS GAMC y mantiene ocultos los GeoJSON sintéticos. El mapa base y las fuentes tipográficas necesitan conexión; la interfaz conserva fuentes de reserva.

## Cartografía

CARTO exige actualmente una clave de basemaps: [documentación oficial](https://www.carto.com/basemaps/apikey/index.html). Se conserva la URL `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png` con parámetro `key` cuando existe `VITE_CARTO_API_KEY`. Sin clave se usa OpenStreetMap con filtro visual oscuro y atribución correcta; se informa el proveedor en el mapa. Esta clave de teselas es pública en el navegador y debe limitarse por origen en CARTO. Nunca reutilizar la MAP_KEY NASA aquí. Reinicia Vite o reconstruye la imagen tras configurarla.

Los dos GeoJSON incluidos contienen un esquema sintético de parque y 15 distritos. `properties.demo=true` impide cargarlos como verificados. En modo conectado se ocultan del mapa. No son cartografía de referencia ni asignan distritos a detecciones reales.

Obtén límites de la autoridad competente (SERNAP/GeoBolivia y municipio) con permiso y procedencia documentados. Sustituye los archivos conservando EPSG:4326. Cada Feature admite:

```json
{"id":"distrito:13","clase":"distrito","nombre":"Distrito 13","distrito":13,"subdistrito":null,"demo":false,"fuente":"institución, fecha, enlace y licencia"}
```

`clase`: `tunari`, `distrito`, `industrial` o `asentamiento`. Las tres primeras requieren Polygon/MultiPolygon; asentamientos también aceptan Point. Importa archivos adicionales con `python scripts/cargar_geometrias.py archivo.geojson --verificadas`. Se aplica un buffer geodésico de 2 km a asentamientos. IDs estables actualizan entidades; no se borran entidades omitidas automáticamente. Importar antes de históricos es más eficiente. Al actualizar cartografía se reclasifican detecciones; reevalúa las alertas y revisa decisiones antiguas. Los archivos deben cubrir todo el ámbito deseado; el bbox de ingesta solicitado cubre solo una parte del parque, no su extensión total.

## Alertas y revisión

Cada señal tiene una clave única unidad/año/semana/señal. Una reevaluación actualiza evidencia sin crear duplicados ni reabrir alertas cerradas. La unidad es distrito verificado o, si falta, celda UTM. Detecciones candidatas aparecen en el mapa, pero no disparan alertas. Una señal satelital no confirma un incendio en terreno.

Críticas: Telegram, cuando está configurado y la revisión está confirmada. Altas: panel. Medias/bajas: dashboard. El worker publica tras confirmar la transacción de evaluación y conserva el estado de envío; errores se reintentan en un ciclo posterior. Un fallo entre recepción Telegram y commit puede duplicar el mensaje (entrega al menos una vez); el ID permite reconocerlo. No se notifican señales con última detección de más de 24 h. Push y SMS no se implementan porque Telegram cubre el canal solicitado sin añadir proveedores.

`falsa_alarma` contribuye a un ajuste acotado por unidad con cierres de los últimos 365 días; no elimina registros originales ni reduce la regla de zona crítica. La confirmación es una afirmación humana: cambiar el estado a «en revisión» por sí solo no confirma el foco.

## Verificación local

Pruebas puras cubren umbrales estrictos, sensores, fechas, regímenes, percentiles, persistencia, clasificación y cobertura. Las pruebas PostGIS usan un esquema temporal independiente de tablas existentes. Se requiere una base de pruebas explícita, nunca la base de operación. El arranque Compose y las consultas geoespaciales deben validarse con Docker/PostGIS disponibles; no se sustituyen por SQLite.

Comprobación del 10 de noviembre de 2026: 43 pruebas pasadas; 3 pruebas PostGIS omitidas por falta de base de pruebas/Docker. `npm run build`, compilación Python y `pip check` correctos. Se verificaron los 65 archivos solicitados, README de 40 líneas, GeoJSON válidos con 15 distritos y YAML Compose. Revisión visual en navegador: fallback explícito, filtro de distrito, cierre como falsa alarma, capas, heatmap, popup y tamaños móvil/escritorio sin desbordamiento horizontal. No se validó ingesta NASA autenticada ni envío Telegram. CARTO sin clave devolvió teselas con marca de restricción; se verificó el respaldo OSM.
