# Verificación local de geometrías

Fecha: 2026-11-11T20:37:30-04:00. Ejecución única; sin fuentes externas.

El esquema usa `unidades_espaciales`, con `clase=distrito` y `clase=tunari`; no existen tablas separadas `distritos` y `pnt`.
Conteo equivalente: 15 distritos + 1 PNT = 16 geometrías.
ST_IsValid: 16/16 válidas. Correcciones ST_MakeValid: 0.

**Validez topológica no acredita límites oficiales.** Se conserva `verificada=false` en las geometrías ilustrativas y no se usan para afirmar el distrito real de un foco.

| ID | Clase | Válida | SRID | Demo | Verificada |
|---|---|---|---|---|---|
| distrito:1 | distrito | True | 4326 | true | False |
| distrito:10 | distrito | True | 4326 | true | False |
| distrito:11 | distrito | True | 4326 | true | False |
| distrito:12 | distrito | True | 4326 | true | False |
| distrito:13 | distrito | True | 4326 | true | False |
| distrito:14 | distrito | True | 4326 | true | False |
| distrito:15 | distrito | True | 4326 | true | False |
| distrito:2 | distrito | True | 4326 | true | False |
| distrito:3 | distrito | True | 4326 | true | False |
| distrito:4 | distrito | True | 4326 | true | False |
| distrito:5 | distrito | True | 4326 | true | False |
| distrito:6 | distrito | True | 4326 | true | False |
| distrito:7 | distrito | True | 4326 | true | False |
| distrito:8 | distrito | True | 4326 | true | False |
| distrito:9 | distrito | True | 4326 | true | False |
| tunari:demo | tunari | True | 4326 | true | False |

## Cruce con detecciones NRT

Detecciones examinadas: 1. Coincidencia exacta con un distrito: 1. Incidencias: 0.

## PNT

- tunari:demo: dentro del bbox=True; solapamiento con 3 distritos (distrito:1, distrito:13, distrito:2). Umbral solicitado ≤3: cumple.

Los cruces usan ST_Contains; un punto sobre un borde puede tener cero coincidencias. El solapamiento del PNT cuenta intersecciones con área positiva. No se corrigieron límites manualmente ni se certificó su procedencia.

## Diagnóstico previo de la mejora del mapa

11 de noviembre de 2026. `\dt` y `\d unidades_espaciales` confirman el esquema real; `distritos` y `pnt` se representan mediante la columna `clase`. Ambos GeoJSON están en `data/geo/`. Hay 15 distritos + 1 PNT, todos válidos; no hizo falta recargar ni aplicar ST_MakeValid.

Áreas calculadas sobre la geometría original con `ST_Area(geom::geography)/1e6`, no superficies oficiales. Intersección mediante `ST_Intersects`.

| ID | Nombre | Válida | Área km² | Interseca PNT |
|---|---|---|---:|---|
| distrito:1 | Distrito 1 · posición ilustrativa | Sí | 10.586 | Sí |
| distrito:2 | Distrito 2 · posición ilustrativa | Sí | 10.586 | Sí |
| distrito:3 | Distrito 3 · posición ilustrativa | Sí | 10.586 | No |
| distrito:4 | Distrito 4 · posición ilustrativa | Sí | 14.112 | No |
| distrito:5 | Distrito 5 · posición ilustrativa | Sí | 14.112 | No |
| distrito:6 | Distrito 6 · posición ilustrativa | Sí | 14.112 | No |
| distrito:7 | Distrito 7 · posición ilustrativa | Sí | 17.636 | No |
| distrito:8 | Distrito 8 · posición ilustrativa | Sí | 17.636 | No |
| distrito:9 | Distrito 9 · posición ilustrativa | Sí | 17.636 | No |
| distrito:10 | Distrito 10 · posición ilustrativa | Sí | 14.112 | No |
| distrito:11 | Distrito 11 · posición ilustrativa | Sí | 14.112 | No |
| distrito:12 | Distrito 12 · posición ilustrativa | Sí | 10.586 | No |
| distrito:13 | Distrito 13 · posición ilustrativa | Sí | 10.586 | Sí |
| distrito:14 | Distrito 14 · posición ilustrativa | Sí | 17.636 | No |
| distrito:15 | Distrito 15 · posición ilustrativa | Sí | 17.636 | No |
| tunari:demo | Parque Nacional Tunari · esquema ilustrativo | Sí | 416.431 | Sí |

La población no consta en los metadatos locales. Se muestra «Sin dato». Los agregados utilizan registros con distrito asignado y eventos históricos importados, sin atribuir oficialmente detecciones a polígonos ilustrativos.
