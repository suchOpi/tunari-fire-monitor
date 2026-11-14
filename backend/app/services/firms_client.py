import csv
import io
import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
import httpx
from ..config import get_settings

SOURCES = {'MODIS_NRT', 'VIIRS_SNPP_NRT', 'VIIRS_NOAA20_NRT', 'VIIRS_NOAA21_NRT',
           'MODIS_SP', 'VIIRS_SNPP_SP', 'VIIRS_NOAA20_SP', 'VIIRS_NOAA21_SP'}

KEYLESS_URLS = {
    'VIIRS_SNPP_NRT': 'https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Global_24h.csv',
    'VIIRS_NOAA20_NRT': 'https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_24h.csv',
    'VIIRS_NOAA21_NRT': 'https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-21-viirs-c2/csv/J2_VIIRS_C2_Global_24h.csv',
    'MODIS_NRT': 'https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_Global_24h.csv',
}
log = logging.getLogger('tunari.sources')


def parse_keyless(lines, bbox):
    reader = csv.DictReader(lines)
    if not {'latitude', 'longitude', 'acq_date', 'acq_time', 'confidence'} <= set(reader.fieldnames or []):
        raise ValueError('CSV FIRMS inválido')
    west, south, east, north = bbox
    rows, total, discarded, missing_type, latest = [], 0, 0, 0, None
    for row in reader:
        total += 1
        stamp = datetime.strptime(f"{row['acq_date']} {str(row['acq_time']).split('.')[0].zfill(4)}", '%Y-%m-%d %H%M').replace(tzinfo=timezone.utc)
        latest = max(latest or stamp, stamp)
        lat, lon = float(row['latitude']), float(row['longitude'])
        if not math.isfinite(lat) or not math.isfinite(lon):
            raise ValueError('Coordenadas inválidas')
        if not west <= lon <= east or not south <= lat <= north:
            continue
        kind = str(row.get('type', '')).strip()
        if kind and float(kind) != 0:
            discarded += 1
            continue
        missing_type += not bool(kind)
        rows.append(row)
    return {'rows': rows, 'filas_globales': total, 'filas_bbox': len(rows), 'excluidas_type': discarded,
            'columna_type': 'type' in reader.fieldnames, 'sin_type': missing_type,
            'datos_hasta': latest.isoformat() if latest else None}


def request_with_backoff(operation):
    for attempt in range(get_settings().nrt_http_retries + 1):
        try:
            return operation(), attempt + 1
        except httpx.HTTPError as error:
            retryable = isinstance(error, httpx.TransportError)
            delay = 2 ** (attempt + 1)
            if isinstance(error, httpx.HTTPStatusError):
                retryable = error.response.status_code in {429, 500, 502, 503, 504}
                if error.response.status_code == 429:
                    try:
                        delay = max(delay, float(error.response.headers.get('retry-after', delay)))
                    except ValueError:
                        retryable = False
            if not retryable or delay > 60 or attempt >= get_settings().nrt_http_retries:
                raise
            time.sleep(delay)


def fetch_nrt_keyless(bbox):
    bounds = tuple(map(float, bbox.split(','))) if isinstance(bbox, str) else tuple(bbox)
    if len(bounds) != 4 or not all(map(math.isfinite, bounds)) or not (-180 <= bounds[0] < bounds[2] <= 180 and -90 <= bounds[1] < bounds[3] <= 90):
        raise ValueError('Bounding box inválido')

    def download(item):
        product, url = item
        def retrieve():
            with httpx.stream('GET', url, timeout=httpx.Timeout(30, connect=5), follow_redirects=False) as response:
                response.raise_for_status()
                def bounded_lines():
                    size = 0
                    for line in response.iter_lines():
                        size += len(line.encode('utf-8')) + 1
                        if size > get_settings().nrt_max_download_mb * 1024 * 1024:
                            raise ValueError('Archivo NASA excede el límite de descarga')
                        yield line
                result = parse_keyless(bounded_lines(), bounds)
                result.update(estado='ok', url=url, modificado_en=response.headers.get('last-modified'), bytes_descargados=response.num_bytes_downloaded)
                return result
        try:
            result, attempts = request_with_backoff(retrieve)
            result['intentos_http'] = attempts
        except (httpx.HTTPError, ValueError, KeyError) as error:
            status = error.response.status_code if isinstance(error, httpx.HTTPStatusError) else type(error).__name__
            log.warning('NASA %s no disponible: %s', product, status)
            result = {'estado': 'error', 'rows': [], 'url': url, 'error': str(status)}
        return product, {**result, 'fuente_datos': 'nasa_keyless', 'consultado_en': datetime.now(timezone.utc).isoformat()}

    with ThreadPoolExecutor(max_workers=3) as executor:
        names = {s.strip() for s in get_settings().firms_sources.split(',')}
        return dict(executor.map(download, [(name, url) for name, url in KEYLESS_URLS.items() if name in names]))


def fetch_gamc():
                                                                                  
    from . import gamc_client
    result = gamc_client.fetch_wms('distritos', {
        'SERVICE': 'WMS', 'VERSION': '1.1.1', 'REQUEST': 'GetMap', 'FORMAT': 'image/png',
        'SRS': 'EPSG:4326', 'BBOX': get_settings().bbox, 'WIDTH': '1', 'HEIGHT': '1', 'LAYERS': '',
    })
    return gamc_client.metadata() if result is not None else None


def fetch_area(source: str, days: int = 2, start: date | None = None) -> list[dict]:
    settings = get_settings()
    if source not in SOURCES or not 1 <= days <= 5:
        raise ValueError('Fuente no admitida o rango fuera de 1–5 días')
    key = settings.firms_map_key.get_secret_value()
    if not key:
        raise RuntimeError('Configura FIRMS_MAP_KEY en .env')
    url = f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{source}/{settings.bbox}/{days}'
    if start:
        url += f'/{start.isoformat()}'
    try:
        def retrieve():
            response = httpx.get(url, timeout=60, follow_redirects=False)
            response.raise_for_status()
            return response
        response, _ = request_with_backoff(retrieve)
    except httpx.HTTPError:
        raise RuntimeError(f'FIRMS no disponible para {source}; comprueba conexión, clave y cuota') from None
    body = response.text.strip()
    if body.lower() == 'no data':
        return []
    reader = csv.DictReader(io.StringIO(body))
    if not {'latitude', 'longitude', 'acq_date', 'acq_time', 'confidence'} <= set(reader.fieldnames or []):
        raise RuntimeError(f'FIRMS no devolvió CSV válido para {source}')
    return list(reader)
