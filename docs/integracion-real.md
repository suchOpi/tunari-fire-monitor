# Integración real: GAMC y NASA FIRMS

## Fuente proporcionada

[Portal API del GAMC](https://recursosgamc.cochabamba.bo/api-doc), proyecto 3 «Harmonization of MODIS and VIIRS» / «Armonización Satelital para Monitoreo de Incendios».

El endpoint documentado es `https://serviciosgamc.cochabamba.bo/api/gs/wms`. Se integran GetMap, GetLegendGraphic y GetFeatureInfo; las dos primeras producen imágenes PNG y GetFeatureInfo devuelve atributos JSON. La clave publicada del proyecto se configura en `.env`; no se incluye en los archivos fuente ni en el ZIP.

| Capa | service_id |
|---|---|
| Periurbanos | c52066a1-32fd-4925-81e0-c2dcb8f4238f |
| Cota 2750 | 297cefa4-0832-42bb-a98e-2cbea989fd9d |
| Límites distritales | 7eb13092-bf0e-493b-aae6-03c43eedda2c |

Son capas territoriales del GAMC. El nombre del proyecto no implica que estas capas contengan focos MODIS/VIIRS, fechas de incendio, FRP ni un flujo de alertas. Cota 2750 no se interpreta como perímetro completo del Parque Nacional Tunari. No se inventan endpoints WFS ni se reconstruyen límites a partir de imágenes.

Se consumen como WMS sobre Leaflet y se consultan sus atributos al hacer clic. La respuesta distrital comprobada contiene `Distrito` (por ejemplo `D10`) y `Comuna`. Para las detecciones se consulta el distrito por ubicación, con máximo 100 consultas nuevas por descarga y reutilización de clasificaciones anteriores. Casos sin coincidencia, ambiguos o fallidos quedan sin distrito; no se asignan por aproximación. Un filtro distrital advierte que excluye esas detecciones. Los GeoJSON de demostración se conservan por compatibilidad, pero no se muestran ni se usan en el modo real.

## Detecciones NASA

[NASA Active Fire Data](https://firms.modaps.eosdis.nasa.gov/active_fire/) publica descargas NRT de 24 h, 48 h y 7 días. Se usa su catálogo real, referenciado por el código oficial de la página: `https://firms.modaps.eosdis.nasa.gov/api/active_fire_files/all?format=json`. Los enlaces de los CSV se leen del catálogo, se restringen al dominio NASA y al directorio `/data/active_fire/`, y no se construyen nombres de productos inexistentes.

La consulta verificada ofreció MODIS, NOAA-20 y NOAA-21 para Sudamérica. S-NPP no estaba en ese catálogo y no se simula ni se incluye como fuente activa. El adaptador normaliza los atributos FIRMS, conserva adquisición UTC, confianza original y FRP, y filtra el bbox `-66.5,-17.6,-65.8,-17.1`. Los CSV públicos no usan la MAP_KEY municipal ni requieren una MAP_KEY NASA. El cliente de Área original permanece disponible para el flujo persistente con su propia clave NASA.

No es una cámara ni una detección instantánea: la actualización depende del sobrevuelo y publicación. La aplicación descarga cada 3 h y consulta su caché desde el navegador cada minuto. El botón Actualizar consulta el estado sin eludir ese intervalo. La caché de observaciones reales está en `data/processed/nrt_cache.json`, excluida del control de versiones y del paquete fuente. Un reinicio reutiliza la fecha del último intento y no repite descargas inmediatamente.

Cada producto informa hora de consulta, `Last-Modified` cuando está disponible, última adquisición regional y errores. Más de 24 h sin publicación identifica una fuente atrasada. Un fallo conserva las observaciones anteriores con procedencia de error; no las sustituye por un CSV vacío. Sin fuente válida, los KPIs no muestran un cero ficticio. La hora de consulta nunca reemplaza la de adquisición.

## API local añadida

- `GET /api/monitoreo`: observaciones NRT y estado de todas las fuentes, filtros de fecha/distrito.
- `GET /api/capas`: catálogo de las tres capas GAMC, sin divulgar la clave.
- `GET /api/gamc/wms?capa=distritos&...`: proxy restringido a las capas y operaciones documentadas; valida dimensiones/BBOX y PNG.
- `GET /api/gamc/consulta?lat=...&lon=...&capa=distritos`: atributos publicados por GAMC en esa ubicación.

`DATABASE_ENABLED=false` permite arrancar FastAPI como monitor real de lectura sin instalar otra base ni reemplazar PostgreSQL por SQLite. Los endpoints que necesitan PostGIS devuelven 503 en ese modo. La interfaz NRT muestra «—» en alertas/históricos y explica el requisito, en lugar de afirmar que el análisis produjo cero alertas. El motor existente, sus estados y pruebas siguen disponibles en el modo PostGIS; el CSV público no alimenta automáticamente esas tablas. El worker de Área y los importadores continúan siendo el flujo persistente, con MAP_KEY NASA e históricos reales.

## Evidencia y límites

Se verificaron respuestas HTTP 200 de las tres capas, PNG válidos y GetFeatureInfo para el centro de Cochabamba (`D10`, comuna `ADELA ZAMUDIO`). Los tres CSV NASA se descargaron y procesaron, y el backend respondió `demo=false`. En la comprobación del 11 de noviembre de 2026 no hubo detecciones dentro del bbox para el intervalo actual de siete días; el archivo contenía dos detecciones MODIS anteriores, adquiridas el 3 de noviembre, con confianza 76 y clasificadas como candidatas. No se cambiaron sus fechas para hacerlas parecer actuales. El resultado puede cambiar en la siguiente publicación; una consulta vacía no descarta fuego.

Verificación final: 61 pruebas pasadas, 3 pruebas PostGIS omitidas y compilación del frontend correcta. Cobertura: validación de CSV, recorte espacial, identidad, ausencia real frente a error, fuente atrasada, conservación de datos con errores, filtros sin distrito inventado, atributos WMS, rechazo de XML como PNG, protección de la clave y bloqueo de mutaciones sin PostGIS. En navegador se comprobó la consulta territorial D10/Comuna ADELA ZAMUDIO y una interrupción real del backend: indicadores vacíos, mensaje de error, ningún mock y recuperación posterior. Las pruebas PostGIS siguen requiriendo una base explícita; no se ejecutaron en este equipo sin Docker.
