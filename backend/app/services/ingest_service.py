import hashlib
import math
from datetime import datetime, timezone
from sqlalchemy import select, text
from geoalchemy2.elements import WKTElement
from ..config import get_settings
from ..models import Deteccion
from .armonizacion import localizar, agrupar


def numero(value):
    if value is None or str(value).strip().lower() in {'', 'nan', 'none', 'null'}:
        return None
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('Valor numérico no finito')
    return number


def normalizar(row: dict, source: str, origin: str):
    sensor = 'MODIS' if source.startswith('MODIS') else 'VIIRS'
    lat, lon = float(row['latitude']), float(row['longitude'])
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError('Coordenadas inválidas')
    acquisition = str(row['acq_time']).strip().split('.')[0].zfill(4)
    fecha = datetime.strptime(f"{row['acq_date']} {acquisition}", '%Y-%m-%d %H%M').replace(tzinfo=timezone.utc)
    confidence = str(row.get('confidence', '')).strip()
    conf = confidence.lower()
    if sensor == 'MODIS':
        score = numero(conf)
        if score is not None and not 0 <= score <= 100:
            raise ValueError('Confianza MODIS fuera de 0–100')
        eligible = score is not None and score > 80
    else:
        eligible = conf in {'n', 'h', 'nominal', 'high'}
        score = {'l': 30, 'low': 30, 'n': 70, 'nominal': 70, 'h': 90, 'high': 90}.get(conf)
    raw_type = numero(row.get('type'))
    if raw_type is not None and raw_type not in {0, 1, 2, 3}:
        raise ValueError('type debe estar entre 0 y 3')
    tipo = int(raw_type) if raw_type is not None else None
    default_sat = 'N20' if 'NOAA20' in source else 'N21' if 'NOAA21' in source else 'N' if 'SNPP' in source else 'unknown'
    satellite = str(row.get('satellite') or default_sat).strip()
    satellite = {'t': 'Terra', 'a': 'Aqua', 'suomi-npp': 'N', 'snpp': 'N', 'npp': 'N', 'noaa-20': 'N20', 'noaa-21': 'N21',
                 'terra': 'Terra', 'aqua': 'Aqua'}.get(satellite.lower(), satellite)
    identity = f'{sensor}|{satellite}|{fecha.isoformat()}|{lat:.5f}|{lon:.5f}'
    frp = numero(row.get('frp'))
    if frp is not None and frp < 0:
        raise ValueError('FRP negativo')
    return dict(clave=hashlib.sha256(identity.encode()).hexdigest(), sensor=sensor, satelite=satellite,
                fuente='nasa_mapkey' if origin == 'nrt' else source, producto=source,
                origen=origin, fecha=fecha, latitude=lat, longitude=lon,
                geom=WKTElement(f'POINT({lon} {lat})', srid=4326), resolucion=1000 if sensor == 'MODIS' else 375,
                frp=frp, confidence=confidence, brightness=numero(row.get('brightness')),
                bright_ti4=numero(row.get('bright_ti4')), tipo=tipo,
                brightness_k=numero(row.get('brightness') if sensor == 'MODIS' else row.get('bright_ti4')),
                confidence_score=score, posible_oclusion=False,
                candidata=not eligible, descartada=tipo in {1, 2, 3}, revision_manual=tipo is None,
                original=dict(row))


def ingerir(db, rows, source: str, origin='nrt', period=None, provider=None):
    db.execute(text('SELECT pg_advisory_xact_lock(734201)'))
    west, south, east, north = map(float, get_settings().bbox.split(','))
    stats = dict(leidas=0, nuevas=0, actualizadas=0, fuera_bbox=0)
    for index, row in enumerate(rows, start=2):
        stats['leidas'] += 1
        try:
            item = normalizar(row, source, origin)
            if provider:
                item['fuente'] = provider
        except (ValueError, KeyError, TypeError):
            raise ValueError(f'Fila {index}: datos FIRMS inválidos; importación revertida') from None
        if period and not period[0] <= item['fecha'].date() <= period[1]:
            raise ValueError(f'Fila {index}: fecha fuera del período declarado')
        if not west <= item['longitude'] <= east or not south <= item['latitude'] <= north:
            stats['fuera_bbox'] += 1
            continue
        existing = db.scalar(select(Deteccion).where(Deteccion.clave == item['clave']))
        if existing and (existing.origen == 'historico' and origin == 'nrt'):
            continue
        location = localizar(db, item['longitude'], item['latitude'])
        industrial = location.pop('industrial')
        item.update(location)
        item['descartada'] = item['descartada'] or industrial
        if existing:
            for key, value in item.items():
                setattr(existing, key, value)
            detection = existing
            stats['actualizadas'] += 1
        else:
            detection = Deteccion(**item)
            db.add(detection)
            stats['nuevas'] += 1
        db.flush()
        agrupar(db, detection)
    return stats
