from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from ..config import get_settings
from ..models import Ingesta, UnidadEspacial


def registrar(db, key, now, estado='ok', detalle=None):
    row = db.scalar(select(Ingesta).where(Ingesta.clave == key))
    if row is None:
        row = Ingesta(clave=key, fuente=key.split(':')[0], origen='control', inicio=now.date(), fin=now.date())
        db.add(row)
    row.fecha, row.estado, row.detalle = now, estado, detalle or {}
    return row


def stamp(value):
    if not value:
        return None
    return value if isinstance(value, datetime) else datetime.fromisoformat(value)


def source_status(item, now, settings):
    if not item:
        return {'estado': 'sin_ingesta', 'consultado_en': None, 'datos_hasta': None}
    detail = dict(item.detalle or {})
    status = item.estado
    age = now - item.fecha
    limit = timedelta(hours=settings.nrt_interval_hours, minutes=settings.nrt_stale_grace_minutes)
    if status == 'ok' and (age > limit or age < -timedelta(minutes=5)):
        status = 'atrasada'
    published = stamp(detail.get('datos_hasta'))
    if status == 'ok' and detail.get('fuente_datos') == 'nasa_keyless':
        if not published or not -timedelta(minutes=5) <= now - published <= timedelta(hours=settings.nrt_source_max_age_hours):
            status = 'atrasada'
    return {**detail, 'estado': status, 'consultado_en': item.fecha.isoformat(), 'datos_hasta': published.isoformat() if published else None}


def read_sources(db, settings, now):
    names = [s.strip() for s in settings.firms_sources.split(',') if s.strip()]
    rows = db.scalars(select(Ingesta).where(Ingesta.origen == 'nrt', Ingesta.fuente.in_(names))
                      .distinct(Ingesta.fuente).order_by(Ingesta.fuente, Ingesta.fecha.desc())).all()
    latest = {r.fuente: r for r in rows}
    return {name: {'producto': name, **source_status(latest.get(name), now, settings)} for name in names}


def evaluation_gate(db, settings=None, now=None, sources=None):
    settings = settings or get_settings()
    now = now or datetime.now(timezone.utc)
    geometries = db.execute(select(UnidadEspacial.clase, UnidadEspacial.distrito)
                           .where(UnidadEspacial.verificada.is_(True))).all()
    districts = {d for kind, d in geometries if kind == 'distrito'}
    verified = set(range(1, 16)) <= districts and any(kind == 'tunari' for kind, _ in geometries)
    reasons = []
    if not verified:
        reasons.append('Se requieren los 15 distritos y el límite del Tunari verificados; las imágenes GAMC no sustituyen esos polígonos.')
    if not settings.alerts_evaluation_enabled:
        reasons.append('Evaluación deshabilitada por configuración (ALERTS_EVALUATION_ENABLED=false).')
    sources = read_sources(db, settings, now) if sources is None else sources
    if not sources or not all(s['estado'] == 'ok' for s in sources.values()):
        reasons.append('La ingesta NRT está incompleta o atrasada.')
    return {'habilitable': not reasons, 'geometrias_verificadas': verified, 'motivo': ' '.join(reasons)}


def operational_state(db, settings, now):
    sources = read_sources(db, settings, now)
    controls = {r.clave: r for r in db.scalars(select(Ingesta).where(Ingesta.origen == 'control')).all()}
    attempt = controls.get('worker:last_attempt')
    success = db.scalar(select(func.max(Ingesta.fecha)).where(Ingesta.origen == 'nrt', Ingesta.estado == 'ok'))
    scheduled = controls.get('worker:last_scheduled')
    complete = bool(sources) and all(s['estado'] == 'ok' for s in sources.values())
    deadline = timedelta(hours=settings.nrt_interval_hours, minutes=settings.nrt_stale_grace_minutes)
    heartbeat = bool(scheduled and timedelta(0) <= now - scheduled.fecha <= deadline)
    auto = settings.nrt_scheduler_enabled
    state = ('continuo' if heartbeat else 'atrasado') if complete and auto else 'manual' if complete else 'atrasado' if success else 'sin_dato'
    gate = evaluation_gate(db, settings, now, sources)
    evaluation = controls.get('evaluador:last_success')
    evaluation_attempt = controls.get('evaluador:last_attempt')
    fresh = bool(evaluation and evaluation.estado == 'ok' and timedelta(0) <= now - evaluation.fecha <= deadline
                 and (not success or evaluation.fecha >= success))
    available = gate['habilitable'] and fresh
    reason = gate['motivo'] or ('' if available else 'No hay una ejecución exitosa reciente del evaluador posterior a la ingesta.')
    if evaluation_attempt and evaluation_attempt.estado == 'error':
        available, reason = False, 'La última ejecución del evaluador falló; se conserva el registro anterior sin considerarlo vigente.'
    warnings = []
    retired = []
    if 'VIIRS_SNPP_NRT' not in sources and now.date().isoformat() >= '2026-11-02':
        retired.append({'producto': 'VIIRS_SNPP_NRT', 'desde': '2026-11-02',
                        'motivo': 'Entrega operativa de Suomi-NPP finalizada; históricos conservados.',
                        'url': 'https://star.nesdis.noaa.gov/icvs/status_NPP_sc.php'})
        warnings.append('Suomi-NPP dejó de entregar datos operativos el 2 de noviembre de 2026; NRT usa MODIS, NOAA-20 y NOAA-21. Sus históricos se conservan.')
    if state in {'atrasado', 'sin_dato'}:
        warnings.append('Datos atrasados o no disponibles; no interpretar los indicadores ausentes como cero incendios.')
    if auto and not heartbeat:
        warnings.append('Sin ejecución programada reciente. Comprueba la tarea de Windows, la sesión y Docker Desktop.')
    return {
        'fuentes': sources, 'completa': complete, 'ultima_ingesta': success.isoformat() if success else None,
        'ultimo_intento': attempt.fecha.isoformat() if attempt else None,
        'ultima_ingesta_completa': max(s['consultado_en'] for s in sources.values()) if complete else controls['worker:last_success'].fecha.isoformat() if 'worker:last_success' in controls else None,
        'proxima_actualizacion': (attempt.fecha + timedelta(hours=settings.nrt_interval_hours)).isoformat() if attempt and auto else None,
        'actualizacion_automatica': auto, 'estado': state, 'intervalo_horas': settings.nrt_interval_hours,
        'ultima_ejecucion_programada': scheduled.fecha.isoformat() if scheduled else None,
        'advertencias': warnings, 'fuentes_retiradas': retired,
        'motor_alertas': {**gate, 'disponible': available, 'motivo': reason,
                          'ultima_ejecucion': evaluation_attempt.fecha.isoformat() if evaluation_attempt else None,
                          'ultima_exitosa': evaluation.fecha.isoformat() if evaluation else None},
    }


def apply_availability(stats, operation, district_verified=True):
                                                                                           
    if not district_verified or (not operation['completa'] and stats['detecciones_hoy'] == 0):
        stats['detecciones_hoy'] = None
    if not operation['motor_alertas']['disponible']:
        stats['alertas_activas'] = None
    stats['disponibilidad'] = {
        'detecciones_hoy': 'sin_dato' if stats['detecciones_hoy'] is None else 'disponible' if operation['completa'] else 'parcial',
        'alertas_activas': 'disponible' if stats['alertas_activas'] is not None else 'sin_dato',
    }
    return stats
