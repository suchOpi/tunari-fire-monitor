# Informes históricos y seguimiento de 2026

Verificación: 13/11/2026, hora de Bolivia.

## Qué impedía incluir 2026

El selector terminaba en el año anterior, la API rechazaba el año actual y el informe leía únicamente `MODIS_SP` de origen histórico. El worker NRT funcionaba, pero esos registros no llegaban a estas cuatro gráficas.

## Cambios aplicados

- Selector y API admiten el año actual. Selección inicial: año anterior–año actual; 2026 está rotulado «en curso».
- Una serie por sensor: MODIS, VIIRS NOAA-20, NOAA-21 y Suomi-NPP histórico. No se suman sensores de distinta resolución ni se reactiva la ingesta del satélite retirado.
- Eventos por año, frecuencia mensual, horas y calendario incluyen los registros NRT guardados del sensor seleccionado. El reemplazo por producto estándar conserva la deduplicación existente.
- Se indican cobertura parcial, fecha de consulta y corte de datos. `—` distingue períodos sin dato o futuros; un cero solo aparece con cobertura conocida del período consultado. Un total parcial no representa todo el año.
- Las ventanas superpuestas de las ingestas se unen. Las tasas y la comparación con IA usan exclusivamente días completos en Bolivia. Los días sin archivo o con consulta parcial no se convierten en ceros de entrenamiento.
- La consulta existente de monitoreo cada 60 s detecta cambios de ingesta y renueva las gráficas. Se conserva la caché de cinco minutos, invalidada por la nueva fecha de ingesta, sin nuevos timers ni descargas al cambiar el gráfico.
- La IA sigue usando años anteriores con archivos estándar MODIS. Al incluir 2026, compara observado/esperado solo sobre días completos consultados, cuando hay modelo y cobertura suficientes. Sigue siendo exploratoria, sin alertas operativas.
- CSV e informe JSON incluyen sensor y cobertura; los gráficos y las fechas distinguen registros de 2025 de los de 2026.

## Resultado real observado

| Serie / verificación | Resultado |
| --- | --- |
| MODIS 2025–2026 | 5 eventos elegibles de 2025; 0 en las ventanas de 2026 consultadas, con cobertura parcial explícita |
| VIIRS NOAA-21, 2026 | 1 detección y 1 evento agrupado real del 11/11/2026 |
| Enero 2026 sin archivo | `null`, no cero |
| Diciembre 2026 futuro | `null`, rotulado futuro en el calendario |
| Tasa 2026 | `null`: todavía no hay días completos consultados; no se calcula una frecuencia anual con una muestra fragmentaria |
| IA 2021–2026 | Entrenamiento 2021–2024, validación 2025, seguimiento de 2026 separado; aún sin días completos comparables |
| Pruebas | 10 pruebas enfocadas de informes/cobertura/IA aprobadas y 1 adicional de comparación actual sin contaminar el entrenamiento; compilación Vite correcta |

No se descargaron datos históricos nuevos ni se ejecutó una ingesta adicional. Solo se consultó el catálogo público: contiene el CSV anual Bolivia 2025, no un archivo anual Bolivia 2026 en esta verificación.

## Para completar los meses de 2026 que faltan

La recolección de 24 h no reconstruye los meses anteriores. Se necesita una importación única del área de Cochabamba/Tunari, con fechas y producto documentados:

1. Obtener los datos oficiales faltantes mediante [NASA Archive Download](https://firms.modaps.eosdis.nasa.gov/download/) (CSV por zona y período, autenticación Earthdata/correo), o configurar localmente una MAP_KEY gratuita y comprobar disponibilidad de fechas en la [API de Área](https://firms.modaps.eosdis.nasa.gov/api/area/). La API admite consultas de 1–5 días; no consultar globalmente todo 2026.
2. Importar cada producto con `backend/scripts/cargar_historico.py`, indicando `--source`, `--inicio` y `--fin` reales. Usar `--completo` únicamente para un archivo estándar `_SP` que cubra todo el período y bbox declarados. Un CSV NRT importado aporta observaciones provisionales, pero no certifica cobertura completa ni entra al entrenamiento; las tasas seguirán sin dato donde no se pueda acreditar el denominador.
3. Conservar la ingesta de 3 h para los nuevos registros. Revisar que los huecos se reduzcan realmente antes de presentar comparaciones anuales. No comparar el acumulado parcial de 2026 con años completos como si tuvieran la misma cobertura.

NASA reemplaza NRT por datos estándar cuando están disponibles, aproximadamente con cinco meses de retraso; por ello no todo 2026 puede considerarse archivo estándar hoy. [Archivo FIRMS](https://firms.modaps.eosdis.nasa.gov/download/).

## Comprobación local

```powershell
curl.exe "http://127.0.0.1:8000/api/informes/historico?desde=2025&hasta=2026&ambito=entorno&sensor=MODIS"
curl.exe "http://127.0.0.1:8000/api/informes/historico?desde=2026&hasta=2026&ambito=entorno&sensor=VIIRS_NOAA21"
curl.exe "http://127.0.0.1:8000/api/informes/historico?desde=2021&hasta=2026&ambito=entorno&sensor=MODIS&formato=csv"
```

Sin cambios de `.env`, sin dependencias, sin nuevas tareas ni contenedores. Costo adicional de servicios: **US$0/mes**. Permanecen las condiciones locales de sesión abierta, equipo encendido, conexión y PostGIS disponible. El refresco es periódico, condicionado a los sobrevuelos y la publicación de NASA; no es streaming ni detección instantánea.
