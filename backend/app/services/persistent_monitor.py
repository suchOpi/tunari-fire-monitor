from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from ..api.routes import detecciones, eventos, alertas, estadisticas
from ..config import get_settings
from ..models import Deteccion
from . import gamc_client


def monitor(db, filters, now=None):
    now = now or datetime.now(timezone.utc)
    settings = get_settings()
    points = detecciones.listar(filters, 5000, db)
    events = eventos.listar(filters, 5000, db)
    alerts = alertas.listar(filters, None, 1000, db)
    stats = estadisticas.resumen_db(filters, db, now, settings)
    operation = stats.pop('monitoreo')
    sources = operation['fuentes']
    provider = 'nasa_mapkey' if settings.firms_map_key.get_secret_value() else 'nasa_keyless'
    usable = any(s['estado'] in {'ok', 'atrasada'} for s in sources.values())
    latest = db.scalar(select(func.max(Deteccion.fecha)))
    stats.update(ultima_deteccion_area=latest.isoformat() if latest else None,
                 registros_area_archivo=db.scalar(select(func.count()).select_from(Deteccion)))
    if not any(row['cobertura'] != 'sin_datos' for row in stats['serie']):
        stats['eventos_historicos'] = None
    notices = list(operation['advertencias'])
    if not operation['motor_alertas']['disponible']:
        notices.append(operation['motor_alertas']['motivo'])
    days = 1 if provider == 'nasa_keyless' else settings.nrt_days
    if filters.inicio < now - timedelta(days=days):
        notices.append(f'Cada ingesta consulta {days * 24} horas; el resto depende de datos guardados previamente.')
    if any(s.get('columna_type') is False or s.get('sin_type') for s in sources.values()):
        notices.append('FIRMS no informa type en parte de los datos; distinguir industria y volcanes requiere revisión.')
    cartography = gamc_client.metadata()
    if cartography.get('disponible') is False:
        notices.append('Cartografía GAMC temporalmente no disponible. Los focos NASA se consultan de forma independiente.')
    return {'demo': False, 'modo': 'postgis', 'fuente_datos': provider,
            'estado': 'ok' if operation['completa'] else 'parcial' if usable else 'no_disponible',
            'detecciones': points['items'], 'eventos': events['items'], 'alertas': alerts['items'],
            'truncado': points['truncado'] or events['truncado'] or alerts['truncado'],
            'consulta': now.isoformat(), 'ultimo_intento': operation['ultimo_intento'],
            'proxima_actualizacion': operation['proxima_actualizacion'],
            'actualizacion_automatica': operation['actualizacion_automatica'],
            'monitoreo': {k: v for k, v in operation.items() if k not in {'fuentes', 'motor_alertas'}},
            'avisos': notices, 'capas': cartography, 'estadisticas': stats,
            'motor_alertas': operation['motor_alertas']}
