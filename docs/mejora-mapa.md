# Mejora del mapa: cierre

Validación final: 12 de noviembre de 2026, America/La_Paz. Diagnóstico previo realizado el 11 de noviembre, antes de modificar código.

Aplicación: http://localhost:5173. Backend: http://localhost:8000. PostGIS saludable; se recuperó el servicio `db`, que estaba detenido al retomar. El volumen conservó 16 geometrías y 1 detección real NASA NOAA-21 del 11 de noviembre. No se ejecutó otra ingesta en esta etapa.

## Archivos modificados

Rutas relativas a `tunari-fire-monitor/`.

| Archivo | Cambio |
|---|---|
| `backend/app/api/routes/geografia.py` | Tres endpoints GeoJSON, simplificación 0.0005, caché de geometrías y agregados PostGIS. |
| `backend/app/main.py` | Registra `/geografia/*` y su alias `/api/geografia/*`. |
| `backend/tests/test_postgis.py` | Dos pruebas de geometrías, agregados, caché, alertas y datos ausentes. |
| `frontend/src/api/client.js` | Cliente de límites y detalle distrital. |
| `frontend/src/context/FiltrosContext.jsx` | Visibilidad y carga compartida de límites una sola vez. |
| `frontend/src/utils/constantes.js` | Lista estática de 15 distritos, bbox general y nombres de capas. |
| `frontend/src/components/FiltrosFecha.jsx` | Retira el selector de distritos; conserva los filtros temporales. |
| `frontend/src/components/PanelDistritos.jsx` | Tarjetas, toggles, selección y detalle bajo demanda. |
| `frontend/src/components/Sidebar.jsx` | Integra el panel distrital. |
| `frontend/src/components/Mapa.jsx` | Límites locales, pane 350, popups, hover, selección y leyenda. |
| `frontend/src/index.css` | Estilos de tarjetas, límites, leyenda y adaptación móvil. |
| `docs/geometrias.md` | Diagnóstico real y tabla de 16 geometrías validadas. |
| `README.md` | Añade ocho líneas sobre endpoints, controles y caché. |
| `docs/mejora-mapa.md` | Este reporte de cierre. |

## Criterios de aceptación

| # | Estado | Criterio y evidencia |
|---|---|---|
| 1 | ✅ | `/geografia/distritos`: HTTP 200, FeatureCollection con 15 features. |
| 2 | ✅ | `/geografia/pnt`: HTTP 200, FeatureCollection con 1 feature. |
| 3 | ✅ | `/geografia/distrito/5`: HTTP 200, geometría y estadísticas; listas vacías donde no existen registros. |
| 4 | ✅ | 15 polígonos distritales, borde gris `#2a3140`, discontinuo `4,4`. |
| 5 | ✅ | PNT verde `#22c55e`, discontinuo `8,4`. |
| 6 | ✅ | Pane de límites z-index 350; focos y alertas 400. El foco real permanece seleccionable. |
| 7 | ✅ | Hover observado: grosor 2 y opacidad 0.3; salida restaura el estilo. |
| 8 | ✅ | Popup distrital muestra nombre, área, alertas activas y eventos históricos. |
| 9 | ✅ | Tarjeta 5 selecciona un polígono naranja, ajusta su bbox y carga el detalle; «Todos» restaura la vista y el foco real. |
| 10 | ✅ | Apagar distritos deja 1 polígono; apagar PNT deja 0; restaurar ambos devuelve 16. |
| 11 | ✅ | Leyenda con Sensores, Límites y Alertas, mediante CSS. |
| 12 | ✅ | `docs/geometrias.md` contiene diagnóstico y tabla de los 15 distritos + PNT válidos. |
| 13 | ✅ | Foco VIIRS real y su popup funcionan; heatmap se añade y retira; controles de alertas y pruebas PostGIS pasan. No hay alertas activas reales para una comprobación visual de su marcador. |

84 pruebas superadas y `npm run build` correcto. Una advertencia de deprecación preexistente de Starlette/httpx. Vista móvil de 390 px sin desbordamiento horizontal. Consola inspeccionada sin errores ni mensajes «Fallback a mock».

Contadores de peticiones de límites permanecieron en 7/7 antes y después de alternar capas y cambiar distritos; no hubo nuevas cargas geométricas por esas interacciones. Las anteriores corresponden a montajes/recargas durante desarrollo y recuperación de PostGIS. Los detalles se consultan bajo demanda. Ninguna dependencia nueva, descarga de geometrías, contenedor adicional ni worker periódico.

## Tabla resumen de geometrías

`unidades_espaciales.clase` distingue distritos y PNT; 16/16 válidas, SRID 4326. No se aplicó ST_MakeValid porque no había geometrías inválidas. Áreas calculadas con ST_Area sobre geography; **son esquemas ilustrativos, no límites oficiales**.

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

La población no está registrada y se presenta «Sin dato». No se asignan oficialmente focos reales a estos polígonos. Los eventos históricos se cuentan por evento distinto con registros históricos importados; no se fabricó historia a partir de NRT.

## Comandos de validación y recuperación

Desde la raíz del proyecto, en PowerShell. La auditoría SQL y las pruebas se hicieron antes del cierre visual; la recuperación de `db` se hizo al retomar.

```powershell
$docker = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe"
& $docker compose up -d db
& $docker compose ps
curl.exe -s -m 10 http://localhost:8000/salud
curl.exe -s -m 15 http://localhost:8000/geografia/distritos
foreach ($endpoint in @('/geografia/pnt','/geografia/distrito/5','/detecciones/recientes','/alertas')) {
    Invoke-WebRequest -Uri ('http://localhost:8000'+$endpoint) -UseBasicParsing -TimeoutSec 15
}
cd backend
.\.venv\Scripts\python.exe -c "import os, pytest; from app.config import get_settings; os.environ['TEST_DATABASE_URL']=get_settings().database_url; raise SystemExit(pytest.main(['-q','-o','faulthandler_timeout=20']))"
cd ../frontend
npm.cmd run build
```

La suite usa esquemas temporales aislados; no introduce alertas ni datos ficticios en las tablas operativas. Diagnóstico previo: `\dt`, `\d unidades_espaciales`, conteos por `clase`, ST_IsValid, ST_Area y ST_Intersects; detalle en `geometrias.md`.

## Pendientes de datos: tres pasos

1. Obtener límites oficiales WGS84 con procedencia documentada y, si se dispone, población distrital con fuente y año. Esta etapa no descarga geometrías externas.
2. Sustituir los GeoJSON locales, cargar con `python scripts/cargar_geometrias.py --verificadas` solo tras acreditar la fuente y repetir la auditoría de validez; reiniciar backend y recargar navegador para renovar cachés.
3. Ejecutar una ingesta reciente y evaluar alertas cuando existan geometrías verificadas y datos suficientes; importar históricos solo en una etapa autorizada. GAMC sigue temporalmente no disponible y no bloquea los focos NASA guardados.

Evidencia visual: `../../tunari-mapa-distritos.jpg`. Paquete actualizado: `../../tunari-fire-monitor.zip`.
