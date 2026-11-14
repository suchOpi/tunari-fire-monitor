from collections import Counter
from datetime import date, datetime, timedelta, timezone
from threading import Lock
from time import monotonic
from zoneinfo import ZoneInfo

from sqlalchemy import text, select, func
from ..config import get_settings
from ..models import Ingesta, UnidadEspacial
from .ia_incendios import analizar, estimar
from .monitoring_state import source_status
from .cobertura_informes import ventanas, dias_completos, horas_en, horas_del_dia

TZ = ZoneInfo('America/La_Paz')
CERCADO_BBOX = [-66.280703, -17.53119, -66.06952, -17.257306]
SENSORES = {'MODIS', 'VIIRS_NOAA20', 'VIIRS_NOAA21', 'VIIRS_SNPP'}
_cache, _lock = {}, Lock()


def clear_cache():
    with _lock:
        _cache.clear()


def informe(db, desde, hasta, distrito=None, ambito='cercado', cached=True, sensor='MODIS', now=None):
    if sensor not in SENSORES:
        raise ValueError('Sensor no admitido')
    now = now or datetime.now(TZ)
    revision = db.scalar(select(func.max(Ingesta.fecha)).where(Ingesta.fuente.in_([sensor + '_SP', sensor + '_NRT'])))
    key = (desde, hasta, distrito, ambito, sensor, revision, now.date())
    with _lock:
        old = _cache.get(key)
        if cached and old and monotonic() - old[0] < 300:
            return old[1]
        result = construir(db, desde, hasta, distrito, ambito, sensor, now)
        if cached:
            if len(_cache) >= 16:
                _cache.pop(next(iter(_cache)))
            _cache[key] = monotonic(), result
        return result


def construir(db, desde, hasta, distrito, ambito, sensor='MODIS', now=None):
    now = (now or datetime.now(TZ)).astimezone(TZ)
    first, last = datetime(desde, 1, 1, tzinfo=TZ), datetime(hasta + 1, 1, 1, tzinfo=TZ)
    params = {'desde': first, 'hasta': min(last, now), 'standard': sensor + '_SP', 'nrt': sensor + '_NRT',
              'distrito': distrito, 'west': CERCADO_BBOX[0], 'south': CERCADO_BBOX[1],
              'east': CERCADO_BBOX[2], 'north': CERCADO_BBOX[3]}
    verified = db.scalar(select(UnidadEspacial.id).where(UnidadEspacial.clase == 'cercado', UnidadEspacial.verificada.is_(True)).limit(1))
    district_verified = distrito is None or db.scalar(select(UnidadEspacial.id).where(
        UnidadEspacial.clase == 'distrito', UnidadEspacial.distrito == distrito, UnidadEspacial.verificada.is_(True)).limit(1)) is not None
    spatial = ''
    if ambito == 'cercado':
        if verified:
            spatial = " AND EXISTS (SELECT 1 FROM unidades_espaciales u WHERE u.clase='cercado' AND u.verificada AND ST_Covers(u.geom,d.geom))"
        else:
            spatial = ' AND d.longitude BETWEEN :west AND :east AND d.latitude BETWEEN :south AND :north'
    where = "d.producto IN (:standard,:nrt) AND d.origen IN ('historico','nrt') AND d.fecha>=:desde AND d.fecha<:hasta" + spatial
    if distrito is not None:
        where += ' AND d.distrito=:distrito'
    if not district_verified:
        where += ' AND FALSE'
    inventory = db.execute(text(f"""SELECT count(*) AS total,
        count(*) FILTER (WHERE d.descartada) AS descartadas,
        count(*) FILTER (WHERE d.candidata AND NOT d.descartada) AS baja_confianza
        FROM detecciones_raw d WHERE {where}"""), params).mappings().one()
    eligible = where + ' AND NOT d.descartada AND NOT d.candidata'
                                                                               
    events = db.execute(text(f"""
        SELECT d.evento_id, min(d.fecha) AS fecha, count(*) AS detecciones,
               max(d.frp) AS frp_max, bool_or(d.revision_manual) AS revision_manual,
               bool_or(d.origen='nrt') AS provisional
        FROM detecciones_raw d WHERE {eligible} AND d.evento_id IS NOT NULL
        GROUP BY d.evento_id ORDER BY fecha
    """), params).mappings().all()
    hourly = dict(db.execute(text(f"SELECT extract(hour from timezone('America/La_Paz',d.fecha))::int, count(*) FROM detecciones_raw d WHERE {eligible} GROUP BY 1"), params).all())
    imports = db.scalars(select(Ingesta).where(Ingesta.fuente.in_([sensor + '_SP', sensor + '_NRT']),
                                              Ingesta.origen.in_(['historico', 'nrt']))).all()
    archive_windows, nrt_windows, windows = ventanas(imports, first, last, now) if district_verified else ([], [], [])
    archive_days, covered_days = dias_completos(archive_windows), dias_completos(windows)
    covered_hours = horas_del_dia(windows)
    counts = Counter(e['fecha'].astimezone(TZ).date() for e in events)
    monthly = Counter()
    for day, count in counts.items():
        monthly[(day.year, day.month)] += count
    samples = [(d, counts.get(d, 0)) for d in sorted(covered_days)]

    def period(start, end):
        days = sum(start.date() <= d < end.date() for d in covered_days)
        duration = (end.date() - start.date()).days
        hours = horas_en(windows, start, end)
        observations = sum(n for d, n in counts.items() if start.date() <= d < end.date())
        known = hours > 0 or observations > 0
        status = 'futuro' if start >= now else 'completa' if days == duration else 'parcial' if known else 'sin_datos'
        return {'eventos': observations if known else None, 'dias_cubiertos': days,
                'horas_consultadas': round(hours, 2), 'cobertura': status,
                'dias_archivo': sum(start.date() <= d < end.date() for d in archive_days)}

    annual = [{'anio': year, **period(datetime(year, 1, 1, tzinfo=TZ), datetime(year+1, 1, 1, tzinfo=TZ)),
               'en_curso': year == now.year} for year in range(desde, hasta+1)]
    calendar = []
    for year in range(desde, hasta+1):
        for month in range(1, 13):
            start = datetime(year, month, 1, tzinfo=TZ)
            end = datetime(year + (month == 12), month % 12 + 1, 1, tzinfo=TZ)
            calendar.append({'mes': f'{year}-{month:02}', **period(start, end)})
    by_month = []
    for month in range(1, 13):
        days = sum(d.month == month for d in covered_days)
        covered_events = sum(n for d, n in samples if d.month == month)
        parts = [p for p in calendar if int(p['mes'][-2:]) == month]
        known = any(p['eventos'] is not None for p in parts)
        by_month.append({'mes': month, 'eventos': sum(n for (y, m), n in monthly.items() if m == month) if known else None,
                         'dias_archivo': sum(d.month == month for d in archive_days), 'dias_cubiertos': days,
                         'cobertura': 'completa' if all(p['cobertura'] == 'completa' for p in parts) else 'parcial' if known else 'sin_datos',
                         'eventos_por_30_dias': round(covered_events / days * 30, 2) if days else None})

                                                                                                        
    training_events = db.execute(text(f"""SELECT min(d.fecha) AS fecha FROM detecciones_raw d
        WHERE {eligible} AND d.producto=:standard AND d.origen='historico'
        AND d.fecha<:year_start AND d.evento_id IS NOT NULL GROUP BY d.evento_id"""),
        {**params, 'year_start': datetime(now.year, 1, 1, tzinfo=TZ)}).scalars().all() if sensor == 'MODIS' else []
    training_counts = Counter(d.astimezone(TZ).date() for d in training_events)
    training_samples = [(d, training_counts.get(d, 0)) for d in sorted(archive_days) if d.year < now.year] if sensor == 'MODIS' else []
    ia = analizar(training_samples, now.date())
    if sensor != 'MODIS':
        ia['motivo'] = 'El modelo existente se entrena con MODIS. Selecciona MODIS y al menos tres años archivados; VIIRS se mantiene separado.'
    current_days = [d for d in covered_days if d.year == now.year]
    if ia['estado'] == 'entrenado' and desde <= now.year <= hasta:
        ia['seguimiento_actual'] = {
            'anio': now.year, 'dias_comparables': len(current_days),
            'eventos_observados': sum(counts.get(d, 0) for d in current_days) if current_days else None,
            'eventos_esperados': round(sum(estimar(ia['coeficientes'], d) for d in current_days), 2) if current_days else None,
            'nota': 'Comparación exploratoria solo sobre días completos consultados; NRT provisional, sin generar alertas.'
        }

    latest_nrt = max((i for i in imports if i.origen == 'nrt'), key=lambda i: i.fecha, default=None)
    status = source_status(latest_nrt, now, get_settings())
    known = bool(windows or events)
    available_years = sorted({y for i in imports if i.origen == 'historico' and i.completa and i.estado == 'ok'
                              for y in range(i.inicio.year, min(i.fin.year, now.year-1)+1)})
    sources = {}
    for item in imports:
        if item.estado != 'ok' or item.fin.year < desde or item.inicio.year > hasta:
            continue
        source = sources.setdefault(item.fuente, {'producto': item.fuente, 'desde': str(item.inicio), 'hasta': str(item.fin),
                                                  'completa': item.origen == 'historico' and item.completa,
                                                  'url': (item.detalle or {}).get('url', 'https://firms.modaps.eosdis.nasa.gov/download/')})
        source['desde'], source['hasta'] = min(source['desde'], str(item.inicio)), max(source['hasta'], str(item.fin))
        source['completa'] = source['completa'] and item.completa
    report = {'generado': now.isoformat(), 'desde': desde, 'hasta': hasta,
              'anios_disponibles': available_years,
              'ambito': ambito, 'distrito': distrito, 'limite_verificado': bool(verified),
              'ambito_descripcion': ('Cercado · límite verificado' if verified else 'Extensión cartográfica GAMC de Cercado; no equivale al límite municipal') if ambito == 'cercado' else 'Área de observación de Cochabamba y Tunari',
              'bbox': CERCADO_BBOX if ambito == 'cercado' else None,
              'sensor': sensor, 'producto': [sensor + '_SP', sensor + '_NRT'],
              'eventos': len(events) if known else None,
              'registros_totales': inventory['total'], 'registros_descartados': inventory['descartadas'],
              'registros_baja_confianza': inventory['baja_confianza'],
              'detecciones': sum(e['detecciones'] for e in events) if known else None,
              'dias_con_eventos': len(counts) if known else None,
              'dias_archivo': len(archive_days), 'dias_cubiertos': len(covered_days),
              'dias_activos_observados': sum(n > 0 for _, n in samples),
              'frecuencia_por_30_dias': round(sum(n for _, n in samples) / len(samples) * 30, 2) if samples else None,
              'primera_observacion': events[0]['fecha'].isoformat() if events else None,
              'ultima_observacion': events[-1]['fecha'].isoformat() if events else None,
              'corte_datos': max([end for _, end in windows] + [e['fecha'] for e in events]).isoformat() if known else None,
              'cobertura_parcial': any(a['cobertura'] != 'completa' for a in annual),
              'incluye_actual': desde <= now.year <= hasta,
              'actualizacion': {'estado': status['estado'], 'ultima_ingesta': latest_nrt.fecha.isoformat() if latest_nrt else None,
                               'datos_hasta': status.get('datos_hasta'), 'automatica': get_settings().nrt_scheduler_enabled,
                               'intervalo_horas': get_settings().nrt_interval_hours},
              'anual': annual, 'mensual': by_month,
              'horaria': [{'hora': h, 'detecciones': hourly.get(h, 0) if h in covered_hours or h in hourly else None} for h in range(24)],
              'calendario': calendar, 'ia': ia,
              'ultimos_eventos': [{'id': e['evento_id'], 'fecha': e['fecha'].isoformat(), 'detecciones': e['detecciones'],
                                   'frp_max': e['frp_max'], 'revision_manual': e['revision_manual'], 'provisional': e['provisional']} for e in events[-30:][::-1]],
              'fuentes': list(sources.values()),
              'advertencias': ['Eventos satelitales agrupados (1.5 km / 24 h), no incendios confirmados.',
                               'Horas de adquisición en Bolivia, no horas de inicio del fuego.',
                               'Cada serie mantiene un solo sensor/producto; MODIS usa confianza >80 y VIIRS confianza nominal o alta.',
                               'NRT es provisional. Una ventana consultada no garantiza observación sin nubes.',
                               'Las tasas usan únicamente días completos consultados; los huecos y meses futuros no son ceros.',
                               'La IA usa archivos estándar de años anteriores, sin entrenar con el año en curso incompleto.']}
    if report['incluye_actual']:
        report['advertencias'].append(f'{now.year} está en curso: solo se muestran observaciones y ventanas guardadas, no el año completo.')
        if status['estado'] != 'ok':
            report['advertencias'].append('La fuente reciente está atrasada o sin dato; consulta la fecha de corte antes de interpretar los gráficos.')
    if not district_verified:
        report['advertencias'].append('Distrito sin límite verificado: no se atribuyen registros a polígonos ilustrativos.')
    ranking = sorted((m for m in by_month if m['eventos_por_30_dias'] is not None), key=lambda m: m['eventos_por_30_dias'], reverse=True)
    report['meses_mayor_frecuencia'] = [m['mes'] for m in ranking[:3] if m['eventos_por_30_dias'] > 0]
    return report
