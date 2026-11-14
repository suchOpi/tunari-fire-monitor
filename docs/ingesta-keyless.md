# Ingesta NASA sin clave — aceptación

Verificación del **11 de noviembre de 2026, 20:37, America/La_Paz**. Una ejecución real del worker; sin instalaciones, contenedores adicionales, históricos ni CSV globales guardados.

## Resultado

| Criterio | Estado | Evidencia |
|---|---|---|
| `db` healthy | ✅ | PostGIS 16-3.4; puerto 127.0.0.1:5432. |
| Recientes no vacío y procedencia admitida | ✅ | HTTP 200, 1 registro, fuente `nasa_keyless`. |
| COUNT detecciones > 0 | ✅ | 1 registro persistido. |
| Foco real visible en el mapa | ✅ | Marcador VIIRS y contador 1; sin mocks. |
| Badge de fuente | ✅ | `Fuente: NASA FIRMS`. |
| `docs/geometrias.md` | ✅ | 16/16 válidas, 1/1 cruce, PNT dentro del bbox y 3 solapamientos. |
| `docs/api_gamc.md` | ✅ | 502 fechado, timeout, pausa y continuidad documentados. |

## Datos conservados

| Campo | Valor |
|---|---|
| Producto | VIIRS_NOAA21_NRT |
| Adquisición | 2026-11-11 05:52 UTC / 01:52 Bolivia |
| Coordenadas | -17.45262, -66.12582 |
| FRP | 0.45 MW |
| brightness_k | 296.26 K |
| Confianza original | nominal |
| Confianza numérica interna | 70; no se utiliza para umbrales VIIRS |
| posible_oclusion | false |
| revision_manual | true; falta type |

Las observaciones satelitales no confirman por sí solas un incendio forestal. Las geometrías siguen marcadas como ilustrativas/no oficiales: la auditoría comprueba topología y coincidencias, no su procedencia. No se modificaron límites.

## Descarga única

| CSV global 24 h | Filas leídas | Retenidas en bbox |
|---|---:|---:|
| Suomi-NPP | 0 | 0 |
| NOAA-20 | 112225 | 0 |
| NOAA-21 | 100774 | 1 |
| MODIS | 21219 | 0 |

Los cuatro CSV respondieron correctamente. Suomi-NPP devolvió solo la cabecera. Se procesaron en streaming con un máximo de tres hilos; no se recurrió a archivos de 7 días ni a la API de Área. Los resultados vacíos se conservaron como tales.

## Comandos ejecutados

Desde `backend`, usando el entorno existente:

```powershell
.\.venv\Scripts\python.exe -c "import os, pytest; from app.config import get_settings; os.environ['TEST_DATABASE_URL'] = get_settings().database_url; raise SystemExit(pytest.main(['-q','-o','faulthandler_timeout=20']))"
.\.venv\Scripts\python.exe -m app.workers.ingesta_nrt
.\.venv\Scripts\python.exe scripts/verificar_geometrias.py
```

Desde `frontend`: `npm run build`. Resultado: 82 pruebas correctas y build correcto. La migración mínima de columnas es idempotente y se ejecuta mediante `init_db()` al iniciar backend/worker.

Desde la raíz:

```powershell
$env:Path = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin;$env:Path"
docker compose ps
curl.exe -sS http://localhost:8000/detecciones/recientes
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT COUNT(*) FROM detecciones_raw;"'
```

El worker finalizó y no queda un bucle de ingesta en segundo plano. Antes de cualquier nueva descarga exige el intervalo persistido de 3 horas. La actualización del frontend solo lee PostGIS y no descarga CSV.
