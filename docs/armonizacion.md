# Armonización y reglas explicables

## Observación y evento

MODIS conserva resolución 1000 m, confianza 0–100 y `brightness`. VIIRS conserva resolución 375 m, confianza original l/n/h o low/nominal/high y `bright_ti4`. FRP está en MW. Se preserva el CSV original y nunca se convierte confianza VIIRS a un porcentaje ficticio.

Identidad: sensor, satélite, adquisición UTC y coordenadas a 5 decimales. No mezcla plataformas distintas. Los CSV SP actualizan una observación NRT equivalente. Si el procesamiento estándar desplaza coordenadas o tiempo, puede conservarse como observación diferente; la agrupación reduce el doble conteo de eventos, pero la correspondencia de productos no es perfecta.

Eventos: distancia geodésica ≤1500 m y ±24 h respecto al primer punto usado como ancla. El ancla queda fija: no hay encadenamiento ilimitado. La ventana completa puede alcanzar 48 h. Se usa la alternativa más cercana, con ID como desempate. La pertenencia puede depender del orden de llegada, por lo que se recomienda importar archivos en orden cronológico; no se fusionan retroactivamente eventos con detecciones puente. Es una agrupación operativa, no un perímetro quemado. El sensor principal es VIIRS si está presente; FRP medio/máximo no se suma entre sensores.

`type=1,2,3` y polígonos industriales verificados descartan puntos antes de agrupar o alertar. Históricos sin `type` y NRT exigen revisión manual. MODIS ≤80 o VIIRS low/desconocido son candidatos; solo MODIS >80 y VIIRS nominal/high contribuyen a anomalías. Los candidatos siguen visibles con menor opacidad.

## Climatología y cobertura

Semanas ISO y días de America/La_Paz, adquisición original UTC. El año actual se excluye de la línea base. 2000–2011 es MODIS dominante; 2012–actualidad es MODIS+VIIRS. 2012 no se cuenta dos veces. El dashboard separa los regímenes sin unirlos con una tendencia continua; los huecos no se convierten a cero. La serie anual resume los archivos importados y se marca parcial cuando no se acredita cobertura anual.

Cada importación registra fuente, fechas y cobertura declarada. Sin `--completo`, sus datos se muestran pero no certifican semanas climatológicas. Este indicador es una declaración del operador sobre un archivo íntegro de Bolivia/área, no una inferencia a partir del número de filas. No certifica ausencia de nubes ni observabilidad satelital perfecta.

Para una semana histórica se requiere cobertura completa de todas las plataformas disponibles entonces: MODIS desde 2000-11-01, S-NPP desde 2012-01-20, NOAA-20 desde 2018-04-01 y NOAA-21 desde 2023-03-01. La cobertura debe incluir el final UTC del domingo boliviano. El archivo 2026 puede estar incompleto; nunca se marca el resto del año como cero. Las semanas con fuentes faltantes no aportan muestras. La semana ISO 53 se compara solo con años que la contienen.

Para cada unidad-semana se cuentan eventos distintos, incluyendo ceros únicamente en semanas cubiertas. Se calcula P95 por interpolación lineal, FRP medio/desviación poblacional/máximo de los máximos por evento y probabilidad de al menos un evento. Se necesitan ≥5 años del mismo régimen. La flota cambia también en 2018 y 2023: el corte de 2012 reduce, pero no elimina, diferencias instrumentales; no interpretar este panel como una estimación causal de tendencia climática.

Se compara la semana actual aún parcial con semanas históricas completas; exceder un umbral es posible desde el inicio, pero no excederlo no descarta anomalía. Persistencia usa los últimos 7 días, incluyendo el cruce de semana/año. Si no hay detección actual, sí hay antecedentes y la cobertura de la base es suficiente, se persiste `posible_oclusion=true` en `evaluaciones_unidad`. No se inventa un evento para representar ausencia ni se diagnostican nubes sin datos de nubes; el indicador solo exige cautela. Detecciones candidatas cuentan como presencia para evitar falsas ausencias.

## Reglas

| Señal | Condición | Nivel |
|---|---|---|
| Frecuencia | Conteo actual > P95 × factor de feedback | Alta |
| Intensidad | Máximo FRP > media + 2σ × factor | Alta |
| Persistencia | ≥3 días consecutivos; ≥5 eleva nivel | Media / alta |
| Fuera de temporada | Probabilidad histórica < 5% / factor | Media |
| Zona crítica | Punto elegible en Tunari o a ≤2 km de asentamiento verificado | Crítica |

No hay regla baja predefinida. El nivel queda soportado por el modelo y la interfaz. Cada alerta explica valores, ventana, años base o geometría. Si σ=0, se compara directamente con la media y se explica dispersión nula; no se divide por cero. Sin datos FRP se omite intensidad, conservando señales de presencia.

Feedback: con al menos 3 cierres por zona en 365 días, factor = 1 + min(0,5; 0,5 × falsas/cerradas). Antes es 1. Se almacena en la evidencia y solo modifica reglas estadísticas futuras; nunca zonas críticas. Este ajuste heurístico no es aprendizaje automático y necesita auditoría operativa.

## Fuentes verificadas al preparar el proyecto

- [NASA FIRMS API de Área](https://firms.modaps.eosdis.nasa.gov/api/area/): CSV, cuatro fuentes NRT, bbox, 1–5 días, 5000 transacciones/10 minutos; con DATE el intervalo empieza en DATE y avanza, no retrocede.
- [NASA FIRMS archivos](https://firms.modaps.eosdis.nasa.gov/download/): CSV anuales y fechas efectivas de productos; NOAA-20 y NOAA-21 no comienzan en 2017/2022 como sus lanzamientos.
- [Solicitud MAP_KEY](https://firms.modaps.eosdis.nasa.gov/api/map_key/).

No se descargaron históricos protegidos ni se hicieron consultas con credenciales. No se confunde un mock con una medición real ni se generan predicciones a partir de estas reglas.
