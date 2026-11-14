# Puesta en marcha — 11 de noviembre de 2026 (Bolivia)

> Informe de la etapa anterior. El estado actual, con ingesta sin clave y una detección real, está en [ingesta-keyless.md](ingesta-keyless.md).

La base y los servidores locales están activos. Falta FIRMS_MAP_KEY; no se ejecutó la ingesta real, conforme a la instrucción recibida.

## Ajustes mínimos

- Compose: solo `db`, imagen fija 16-3.4, volumen nombrado, healthcheck y loopback solicitados.
- `init.sql` habilita PostGIS e incluye `crear_tablas.sql`; existen las tres tablas requeridas y sus auxiliares.
- `.env` coherente con PostgreSQL local. Frontend usa el proxy `/api` de Vite.
- `/api/monitoreo` lee PostGIS, sin descargas regionales automáticas ni fallback a mocks.
- Rutas de aceptación `/salud`, `/detecciones/recientes` y `/alertas`. Recientes identifica las plataformas VIIRS por su fuente; el mapa conserva la familia MODIS/VIIRS.
- Worker de un ciclo por defecto; `--loop` requiere activación explícita. Sin clave termina antes de conectar a la base.
- Logo, favicon y paleta conservados.

## Criterios

| Criterio | Estado | Evidencia |
|---|---|---|
| db healthy | ✅ | PostGIS 16-3.4; 127.0.0.1:5432. |
| `/salud` HTTP 200 | ✅ | PostGIS 3.4, persistencia true. |
| `/detecciones/recientes` no vacío, sensores reales | ❌ | HTTP 200 con `[]`; falta MAP_KEY y no hubo ingesta. |
| `/alertas` devuelve array | ✅ | HTTP 200 con `[]`. |
| Frontend con mapa y focos reales | ❌ | HTTP 200, mapa base cargado; cero focos guardados. GAMC respondió 502. |
| Sin `[API] Fallback a mock` | ✅ | Consola y cliente revisados. |
| `COUNT(*) FROM detecciones_raw > 0` | ❌ | Resultado 0; no se insertaron detecciones de ejemplo. |

## Comandos ejecutados, en orden

Las carpetas se expresan desde la raíz del proyecto. Los servidores se iniciaron en segundo plano, con ventanas ocultas y registros en `work/` del espacio de trabajo.

1. `docker compose up -d db`: falló por PATH. Tampoco estaba disponible la ruta habitual de Program Files.
2. Tras recibir la ruta del usuario: `rg --files "$env:LOCALAPPDATA\Programs\DockerDesktop" -g docker.exe -g docker-compose.exe`.
3. Se ejecutó el CLI encontrado con `compose up -d db`: el motor aún no respondía. `--context desktop-linux` tampoco estaba creado.
4. Desde backend: `python -m venv .venv` y `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.
5. `Start-Process -FilePath "$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe" -WindowStyle Hidden`. El intento durante el arranque devolvió 500; después `compose ps` respondió sin contenedores.
6. Con el motor disponible, desde la raíz:

```powershell
$env:Path = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin;$env:Path"
docker compose up -d db
docker compose ps
```

7. Espera de `healthy` cada 10 s, máximo 60 s, sin reiniciar el contenedor.
8. Desde backend: `.\.venv\Scripts\python.exe scripts/cargar_geometrias.py` → 16 geometrías, verificadas=False.
9. **Omitido:** `python -m app.workers.ingesta_nrt`, porque FIRMS_MAP_KEY está vacía. Está preparado para ejecutar un solo ciclo.
10. Desde frontend: `npm install`, `npm run build`. Desde backend:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -c "import os, pytest; from app.config import get_settings; os.environ['TEST_DATABASE_URL'] = get_settings().database_url; raise SystemExit(pytest.main(['tests/test_postgis.py','-vv','-o','faulthandler_timeout=20']))"
.\.venv\Scripts\python.exe -m pytest tests/test_persistent_api.py -q
```

Resultado: 63 casos sin PostGIS, 5 casos PostGIS y 2 casos nuevos adicionales del worker: 70 únicos superados. Una pasada conjunta quedó esperando conexión y se detuvo; el fixture ahora limita esa conexión a 5 s. No quedaron esquemas de pruebas ni datos de ejemplo en las tablas públicas. La advertencia de deprecación Starlette/httpx no bloquea las pruebas.

11. Se detuvieron únicamente los procesos anteriores de esta app y se ejecutó, en terminales separadas:

```powershell
# backend
.\.venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000 --reload-dir app
# frontend
npm run dev
```

12. Verificación final desde la raíz:

```powershell
docker compose ps
curl.exe -sS -w '\nHTTP %{http_code}\n' http://localhost:8000/salud
curl.exe -sS -w '\nHTTP %{http_code}\n' http://localhost:8000/detecciones/recientes
curl.exe -sS -w '\nHTTP %{http_code}\n' http://localhost:8000/alertas
curl.exe -sS -o NUL -w 'Frontend HTTP %{http_code}\n' http://localhost:5173
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT COUNT(*) FROM detecciones_raw;"'
```

13. Navegador: mapa base y marca visibles, estado «Sin ingesta NRT», fuentes pendientes y ausencia de fallback. Tanto el proxy como la consulta directa al proveedor GAMC devolvieron HTTP 502.

## Pendientes en tres pasos

1. Solicitar la clave en [NASA FIRMS MAP_KEY](https://firms.modaps.eosdis.nasa.gov/api/map_key/) y guardarla únicamente en `.env` como `FIRMS_MAP_KEY`. Se entrega por correo; no es la clave WMS municipal.
2. Conseguir límites oficiales WGS84, reemplazar los ilustrativos en `data/geo/` y ejecutar `python scripts/cargar_geometrias.py --verificadas`. Revisar GAMC cuando el proveedor restablezca el servicio.
3. Ejecutar `python -m app.workers.ingesta_nrt` una vez, reiniciar uvicorn para recargar `.env` y repetir la aceptación. La ventana es de 2 días; una respuesta real vacía debe conservarse como tal. El histórico completo queda fuera de esta fase.
