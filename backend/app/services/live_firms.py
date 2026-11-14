import csv
import io
import json
import logging
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from threading import Lock
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
import httpx
from ..config import get_settings
from .ingest_service import normalizar
from . import gamc_client

ORIGIN = 'https://firms.modaps.eosdis.nasa.gov'
CATALOG = ORIGIN + '/api/active_fire_files/all?format=json'
SOURCES = {'modis': 'MODIS_NRT', 'suomi': 'VIIRS_SNPP_NRT', 'noaa20': 'VIIRS_NOAA20_NRT', 'noaa21': 'VIIRS_NOAA21_NRT'}
TZ = ZoneInfo('America/La_Paz')
FIELDS = ('sensor', 'satelite', 'fecha', 'latitude', 'longitude', 'resolucion', 'frp', 'confidence',
          'brightness', 'bright_ti4', 'candidata', 'revision_manual', 'tipo')
_lock = Lock()
_snapshot = None


def parse_csv(body, source, bbox):
    reader = csv.DictReader(io.StringIO(body.lstrip('\ufeff')))
    if not {'latitude', 'longitude', 'acq_date', 'acq_time', 'confidence'} <= set(reader.fieldnames or []):
        raise ValueError('FIRMS no devolvió un CSV de detecciones')
    west, south, east, north = bbox
    rows, latest = {}, None
    for row in reader:
        stamp = f"{row['acq_date']} {str(row['acq_time']).strip().split('.')[0].zfill(4)}"
        latest = max(latest or stamp, stamp)
        lat, lon = float(row['latitude']), float(row['longitude'])
        if not math.isfinite(lat) or not math.isfinite(lon):
            raise ValueError('Coordenadas FIRMS inválidas')
        if not west <= lon <= east or not south <= lat <= north:
            continue
        item = normalizar(row, source, 'nrt')
        if item['descartada']:
            continue
        value = {name: item[name] for name in FIELDS}
        value.update(id=item['clave'], fecha=item['fecha'].isoformat(), fuente=source, distrito=None,
                     en_tunari=None, hex_id=None, clasificacion_distrito='pendiente')
        rows[value['id']] = value
    last = datetime.strptime(latest, '%Y-%m-%d %H%M').replace(tzinfo=timezone.utc).isoformat() if latest else None
    return list(rows.values()), last


def csv_url(path):
    url = ORIGIN + path if isinstance(path, str) and path.startswith('/') else path
    parsed = urlparse(url or '')
    if parsed.scheme != 'https' or parsed.netloc != 'firms.modaps.eosdis.nasa.gov' or not parsed.path.startswith('/data/active_fire/') or not parsed.path.endswith('_7d.csv'):
        raise ValueError('El catálogo devolvió una URL no permitida')
    return url


def download(item):
    sensor, path = item
    url = csv_url(path)
    response = httpx.get(url, timeout=60)
    response.raise_for_status()
    points, latest = parse_csv(response.text, SOURCES[sensor], tuple(map(float, get_settings().bbox.split(','))))
    modified = response.headers.get('last-modified')
    modified = parsedate_to_datetime(modified).isoformat() if modified else None
    return {'estado': 'ok', 'url': url, 'producto': SOURCES[sensor], 'consultado_en': datetime.now(timezone.utc).isoformat(),
            'modificado_en': modified, 'datos_hasta': latest, 'detecciones': points}


def cache_file():
    return get_settings().data_dir / 'processed' / 'nrt_cache.json'


def snapshot():
    global _snapshot
    with _lock:
        now = datetime.now(timezone.utc)
        if _snapshot is None:
            try:
                candidate = json.loads(cache_file().read_text(encoding='utf-8'))
                _snapshot = candidate if candidate.get('version') == 1 and candidate.get('bbox') == get_settings().bbox else {}
            except (OSError, ValueError):
                _snapshot = {}
        previous = _snapshot
        attempted = previous.get('ultimo_intento')
        interval = timedelta(hours=get_settings().nrt_interval_hours)
        if attempted and now - datetime.fromisoformat(attempted) < interval:
            return previous
        result = {'version': 1, 'bbox': get_settings().bbox, 'ultimo_intento': now.isoformat(), 'fuentes': {}}
        try:
            response = httpx.get(CATALOG, timeout=30)
            response.raise_for_status()
            catalog = response.json()['csv']
            items = [(sensor, next(path for path in regions['South America'] if path.endswith('_7d.csv')))
                     for sensor, regions in catalog.items() if sensor in SOURCES and 'South America' in regions]
            if not items:
                raise ValueError('Catálogo FIRMS sin productos regionales')
            with ThreadPoolExecutor(max_workers=4) as executor:
                pending = {sensor: executor.submit(download, (sensor, path)) for sensor, path in items}
                for sensor, future in pending.items():
                    try:
                        result['fuentes'][sensor] = future.result()
                    except Exception:
                        old = previous.get('fuentes', {}).get(sensor, {})
                        result['fuentes'][sensor] = {**old, 'estado': 'error', 'producto': SOURCES[sensor],
                                                   'error': 'No se pudo obtener o validar este CSV de FIRMS'}
        except Exception:
            result['error_catalogo'] = 'No se pudo consultar el catálogo de archivos públicos de FIRMS'
            result['fuentes'] = {name: {**source, 'estado': 'error'} for name, source in previous.get('fuentes', {}).items()}
        old_points = {d['id']: d for source in previous.get('fuentes', {}).values() for d in source.get('detecciones', [])}
        remaining = 100
        for source in result['fuentes'].values():
            for point in source.get('detecciones', []):
                old = old_points.get(point['id'], {})
                if old.get('clasificacion_distrito') in {'consultado', 'sin_coincidencia'}:
                    point.update(distrito=old.get('distrito'), clasificacion_distrito=old['clasificacion_distrito'])
                elif get_settings().gamc_wms_key.get_secret_value() and remaining:
                    remaining -= 1
                    try:
                        district = gamc_client.district_at(point['longitude'], point['latitude'])
                        point.update(distrito=district, clasificacion_distrito='consultado' if district else 'sin_coincidencia')
                    except (ValueError, RuntimeError):
                        point['clasificacion_distrito'] = 'no_disponible'
        _snapshot = result
        try:
            path = cache_file()
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix('.tmp')
            temporary.write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
            temporary.replace(path)
        except OSError:
            logging.getLogger('tunari').warning('No se pudo guardar la caché NRT; se conserva en memoria')
        return result


def monitor(filters, now=None):
    now = now or datetime.now(timezone.utc)
    state = snapshot()
    sources, all_points = {}, {}
    for name, value in state.get('fuentes', {}).items():
        source = {key: val for key, val in value.items() if key != 'detecciones'}
        stamp = source.get('modificado_en') or source.get('datos_hasta')
        if source.get('estado') == 'ok' and (not stamp or now - datetime.fromisoformat(stamp) > timedelta(hours=24)):
            source['estado'] = 'atrasada'
        sources[name] = source
        for point in value.get('detecciones', []):
            all_points[point['id']] = {**point, 'fuente_estado': source['estado']}
    usable = any(s.get('consultado_en') for s in sources.values())
    complete = bool(sources) and all(s.get('estado') == 'ok' for s in sources.values()) and not state.get('error_catalogo')
    points = [p for p in all_points.values() if filters.inicio <= datetime.fromisoformat(p['fecha']) < filters.fin
              and (not filters.distrito or p['distrito'] == filters.distrito)]
    points.sort(key=lambda p: p['fecha'], reverse=True)
    today = now.astimezone(TZ).date()
    count_today = sum(datetime.fromisoformat(p['fecha']).astimezone(TZ).date() == today for p in all_points.values()
                      if not filters.distrito or p['distrito'] == filters.distrito)
    errors = [state['error_catalogo']] if state.get('error_catalogo') else []
    if filters.inicio < now - timedelta(days=7):
        errors.append('La descarga NRT solo cubre el archivo reciente de 7 días; fechas anteriores requieren históricos.')
    if filters.distrito and any(p['distrito'] is None for p in all_points.values()):
        errors.append('El filtro de distrito excluye detecciones sin distrito identificado por GAMC.')
    return {'demo': False, 'modo': 'nrt', 'estado': 'ok' if complete else 'parcial' if usable else 'no_disponible',
            'detecciones': points, 'eventos': [], 'alertas': [], 'truncado': False,
            'consulta': now.isoformat(), 'ultimo_intento': state.get('ultimo_intento'),
            'proxima_actualizacion': (datetime.fromisoformat(state['ultimo_intento']) + timedelta(hours=get_settings().nrt_interval_hours)).isoformat(),
            'avisos': errors, 'capas': gamc_client.metadata(),
            'estadisticas': {'detecciones_hoy': count_today if complete or (usable and count_today > 0) else None, 'alertas_activas': None, 'eventos_historicos': None,
                             'serie': [], 'fuentes': sources, 'ultima_ingesta': max((s.get('consultado_en', '') for s in sources.values()), default=None),
                             'ultima_deteccion_area': max((p['fecha'] for p in all_points.values()), default=None),
                             'registros_area_archivo': len(all_points), 'climatologia_disponible': False,
                             'posible_oclusion': None, 'geometrias_verificadas': 0, 'tunari_verificado': False},
            'motor_alertas': {'disponible': False, 'motivo': 'Las anomalías requieren históricos y clasificación espacial en PostGIS. Las capas WMS no delimitan todo el PNT.'}}


def run(stop):
    while not stop.is_set():
        try:
            snapshot()
        except Exception as error:
            logging.getLogger('tunari').error('Consulta NRT fallida: %s', type(error).__name__)
        stop.wait(60)
