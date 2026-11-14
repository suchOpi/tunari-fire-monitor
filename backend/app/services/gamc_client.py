import math
import re
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from threading import Lock
import httpx
from ..config import get_settings

ENDPOINT = 'https://serviciosgamc.cochabamba.bo/api/gs/wms'
DOCUMENTATION = 'https://recursosgamc.cochabamba.bo/api-doc'
LAYERS = {
    'periurbanos': {'id': 'c52066a1-32fd-4925-81e0-c2dcb8f4238f', 'nombre': 'Periurbanos'},
    'cota2750': {'id': '297cefa4-0832-42bb-a98e-2cbea989fd9d', 'nombre': 'Cota 2750'},
    'distritos': {'id': '7eb13092-bf0e-493b-aae6-03c43eedda2c', 'nombre': 'Límites distritales'},
}
_status = {}
_lock = Lock()
_request_lock = Lock()


def availability():
    try:
        state = json.loads((get_settings().data_dir / 'processed/gamc_status.json').read_text(encoding='utf-8'))
        if datetime.now(timezone.utc) - datetime.fromisoformat(state['fecha']) < timedelta(minutes=10):
            return state
    except (OSError, ValueError, KeyError):
        pass
    return {'disponible': None}


def save_availability(available, error=None):
    state = {'disponible': available, 'fecha': datetime.now(timezone.utc).isoformat(), 'error': error}
    path = get_settings().data_dir / 'processed/gamc_status.json'
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f'.{os.getpid()}.tmp')
        temporary.write_text(json.dumps(state), encoding='utf-8')
        temporary.replace(path)
    except OSError:
        pass
    return state


def metadata():
    with _lock:
        return {'proveedor': 'GAMC', 'documentacion': DOCUMENTATION,
                'configurado': bool(get_settings().gamc_wms_key.get_secret_value()),
                **availability(),
                'nota': 'Cartografía territorial; no son detecciones de fuego ni el límite completo del PNT.',
                'servicios': [{'capa': key, **value, 'url': f'/api/gamc/wms?capa={key}',
                               **_status.get(key, {})} for key, value in LAYERS.items()]}


def fetch_wms(layer, params):
    key = get_settings().gamc_wms_key.get_secret_value()
    if layer not in LAYERS:
        raise ValueError('Capa GAMC desconocida')
    if not key:
        return None
    with _request_lock:
        if availability()['disponible'] is False:
            return None
        return _fetch_wms(layer, params, key)


def _fetch_wms(layer, params, key):
    query = {'key': key, 'service_id': LAYERS[layer]['id'], **params}
    try:
        response = httpx.get(ENDPOINT, params=query, timeout=5)
        response.raise_for_status()
        if params['REQUEST'] == 'GetFeatureInfo':
            body = response.json()
            if body.get('type') != 'FeatureCollection' or not isinstance(body.get('features'), list):
                raise ValueError('Respuesta GAMC inválida')
        elif not response.content.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('GAMC no devolvió una imagen PNG')
        with _lock:
            _status[layer] = {'estado': 'ok', 'ultima_consulta': datetime.now(timezone.utc).isoformat()}
        save_availability(True)
        return response
    except (httpx.HTTPError, ValueError) as error:
        with _lock:
            _status[layer] = {'estado': 'error', 'ultima_consulta': datetime.now(timezone.utc).isoformat()}
        code = error.response.status_code if isinstance(error, httpx.HTTPStatusError) else type(error).__name__
        save_availability(False, str(code))
        logging.getLogger('tunari.sources').warning('GAMC %s, usando fallback NASA', code)
        return None


def feature_info(layer, lon, lat):
    if not math.isfinite(lon) or not math.isfinite(lat) or not -180 <= lon <= 180 or not -90 <= lat <= 90:
        raise ValueError('Coordenadas inválidas')
    params = {'SERVICE': 'WMS', 'VERSION': '1.1.1', 'REQUEST': 'GetFeatureInfo', 'SRS': 'EPSG:4326',
              'BBOX': f'{lon - .001},{lat - .001},{lon + .001},{lat + .001}',
              'WIDTH': '101', 'HEIGHT': '101', 'X': '50', 'Y': '50',
              'INFO_FORMAT': 'application/json', 'FEATURE_COUNT': '5'}
    response = fetch_wms(layer, params)
    if response is None:
        return None
    result = response.json()
    return [f.get('properties', {}) for f in result['features']]


def district_at(lon, lat):
    features = feature_info('distritos', lon, lat)
    if features is None:
        return None
    ids = {int(match.group(1)) for feature in features
           if (match := re.fullmatch(r'D?(\d{1,2})', str(feature.get('Distrito', '')).strip(), re.I))}
    valid = [value for value in ids if 1 <= value <= 15]
    return valid[0] if len(valid) == 1 else None
