# GAMC y continuidad del servicio

Fecha de verificación: **11 de noviembre de 2026**, America/La_Paz.

- Se observó HTTP **502** del servicio WMS GAMC durante la puesta en marcha. La integración conserva las capas de distritos, periurbanos y cota 2750.
- Cada llamada tiene timeout de **5 segundos**. Un fallo devuelve `None` internamente y registra un único warning: `GAMC 502, usando fallback NASA` (u otro código/error recibido).
- La ingesta consulta la disponibilidad cartográfica como máximo una vez por ejecución; su resultado no impide descargar ni guardar los focos NASA.
- Un fallo se comparte entre backend y worker mediante `data/processed/gamc_status.json`, sin claves, durante 10 minutos. Así se evitan solicitudes repetidas de teselas al proveedor caído. Después se permite una nueva comprobación sin bucles.
- El frontend oculta temporalmente las capas no disponibles, conserva el mapa base y muestra **Fuente: NASA FIRMS** con `fuente_datos=nasa_keyless` o `nasa_mapkey`.
- GAMC proporciona cartografía, no un feed de incendios. Su recuperación reactiva la cartografía; **no cambia la procedencia de los focos NASA a GAMC**. Si se conecta un feed real GAMC en el futuro, el badge ya admite `fuente_datos=gamc`.
- El proxy local existente se conserva para proteger la clave WMS; no se añadieron proxies alternativos para eludir el 502.

Documentación del proveedor: https://recursosgamc.cochabamba.bo/api-doc.

## Fuente de incendios

Sin MAP_KEY, el worker descarga una vez los cuatro CSV globales de **24 h** indicados en `app/services/firms_client.py`, en un máximo de tres hilos. Procesa filas en streaming y solo retiene el bbox `-66.5,-17.6,-65.8,-17.1`; no guarda los CSV globales completos.

Con MAP_KEY configurada usa exclusivamente la API de Área. No mezcla los dos modos durante una ejecución; la identidad de detección permite deduplicar al cambiar de modo.

El intervalo de 3 horas se controla mediante bloqueo PostGIS y fecha persistida antes de descargar, incluso si una descarga falla; supera el mínimo solicitado de 10 minutos. El worker sigue ejecutándose una sola vez por defecto y no queda un proceso periódico activo.

Los cuatro archivos consultados no contenían columna `type`. Se conserva `revision_manual=true`: el filtrado de industria/volcanes queda pendiente para esos registros. Si `type` está presente se excluyen valores distintos de 0. `confidence_score` es solo almacenamiento; las alertas VIIRS siguen utilizando la confianza textual original.
