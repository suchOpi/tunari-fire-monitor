from collections import defaultdict
from dataclasses import asdict
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
import httpx
from sqlalchemy import select, text, func, or_, and_
from ..config import get_settings
from ..models import Alerta, Deteccion, EvaluacionUnidad, Ingesta
from .monitoring_state import evaluation_gate
from .anomalias import climatologia, evaluar, factor_feedback, regimen

TZ = ZoneInfo('America/La_Paz')
AVAILABLE = {'MODIS': date(2000, 11, 1), 'VIIRS_SNPP': date(2012, 1, 20),
             'VIIRS_NOAA20': date(2018, 4, 1), 'VIIRS_NOAA21': date(2023, 3, 1)}


def unidad(d):
    return f'distrito:{d.distrito}' if d.distrito else d.hex_id


def anios_cubiertos(ingestas, week: int, current_year: int):
    years = []
    for year in range(2000, current_year):
        if regimen(year) != regimen(current_year):
            continue
        try:
            start = date.fromisocalendar(year, week, 1)
        except ValueError:
            continue
        end = start + timedelta(days=7)                                               
        expected = [source for source, since in AVAILABLE.items() if since <= start]
        if not expected or start < AVAILABLE['MODIS']:
            continue
        if all(any(i.completa and i.estado == 'ok' and i.fuente.removesuffix('_SP').removesuffix('_NRT') == source
                   and i.inicio <= start and i.fin >= end for i in ingestas) for source in expected):
            years.append(year)
    return years


def evaluar_actualizacion(db, now=None):
    db.execute(text('SELECT pg_advisory_xact_lock(734201)'))
    now = now or datetime.now(timezone.utc)
    gate = evaluation_gate(db, now=now)
    if not gate['habilitable']:
        return {'estado': 'deshabilitada', 'motivo': gate['motivo'], 'unidades': 0, 'nuevas_alertas': 0}
    local = now.astimezone(TZ)
    year, week, _ = local.isocalendar()
    monday = local.date() - timedelta(days=local.weekday())
    start = datetime.combine(monday, time.min, TZ)
    ingestas = db.scalars(select(Ingesta).where(Ingesta.origen == 'historico')).all()
    years = anios_cubiertos(ingestas, week, year)
    local_date = func.timezone('America/La_Paz', Deteccion.fecha)
    records = db.scalars(select(Deteccion).where(
        Deteccion.descartada.is_(False), Deteccion.fecha <= now,
        or_(Deteccion.fecha >= start - timedelta(days=7),
            and_(Deteccion.origen == 'historico', func.extract('week', local_date) == week,
                 func.extract('isoyear', local_date).in_(years)))
    )).all()
    historical, current, recent, observed = defaultdict(list), defaultdict(list), defaultdict(list), set()
    for d in records:
        key = unidad(d)
        day = d.fecha.astimezone(TZ).date()
        iso = day.isocalendar()
        if d.fecha >= start:
            observed.add(key)
            if not d.candidata:
                current[key].append(d)
        if not d.candidata and local.date() - timedelta(days=6) <= day <= local.date():
            recent[key].append(d)
        if not d.candidata and d.origen == 'historico' and iso.year in years and iso.week == week:
            historical[key].append(d)
    units = set(historical) | set(current) | observed
    created = 0
    triggered = set()
    for key in units:
        samples = []
        for sample_year in years:
            items = [d for d in historical[key] if d.fecha.astimezone(TZ).isocalendar().year == sample_year]
            event_frps = defaultdict(list)
            for d in items:
                if d.evento_id is not None:
                    event_frps[d.evento_id].extend([d.frp] if d.frp is not None else [])
            samples.append(dict(eventos=len(event_frps), frps=[max(v) for v in event_frps.values() if v]))
        baseline = climatologia(samples)
        enough = baseline is not None and baseline.anios >= get_settings().min_baseline_years
        eval_key = f'{key}:{year}:{week}'
        evaluation = db.get(EvaluacionUnidad, eval_key) or EvaluacionUnidad(clave=eval_key, unidad_id=key, anio=year, semana=week, regimen=regimen(year))
        evaluation.cobertura_suficiente = enough
        evaluation.posible_oclusion = bool(enough and baseline.probabilidad > 0 and key not in observed)
        evaluation.climatologia = asdict(baseline) if baseline else {'anios': 0}
        evaluation.fecha = now
        db.add(evaluation)
        points = current[key]
        if not points:
            continue
        closed = db.scalars(select(Alerta).where(Alerta.unidad_id == key, Alerta.estado.in_(['atendida', 'falsa_alarma']),
                                                Alerta.fecha >= now - timedelta(days=365))).all()
        factor = factor_feedback(sum(a.estado == 'falsa_alarma' for a in closed), len(closed))
        frps = [d.frp for d in points if d.frp is not None]
        signals = evaluar(len({d.evento_id for d in points if d.evento_id is not None}), max(frps) if frps else None,
                          [d.fecha.astimezone(TZ).date() for d in recent[key]],
                          any(d.en_tunari or d.cerca_asentamiento for d in points), baseline,
                          factor, get_settings().min_baseline_years)
        for signal in signals:
            alert_key = f'{eval_key}:{signal["senal"]}'
            triggered.add(alert_key)
            alert = db.scalar(select(Alerta).where(Alerta.clave == alert_key))
            candidates = [d for d in points if d.en_tunari or d.cerca_asentamiento] if signal['senal'] == 'zona_critica' else points
            point = max(candidates, key=lambda d: d.fecha)
            if not alert:
                alert = Alerta(clave=alert_key, unidad_id=key, evento_id=point.evento_id,
                               distrito=point.distrito, latitude=point.latitude, longitude=point.longitude,
                               fecha=now, revision_manual=any(d.revision_manual for d in candidates),
                               estado='nueva', **signal)
                db.add(alert)
                created += 1
            if alert.estado in {'nueva', 'en_revision'}:
                alert.nivel = signal['nivel']
                alert.descripcion = signal['descripcion']
                alert.actualizada = now
                alert.detalle = {'factor_feedback': factor, 'anios_base': years, 'regimen': regimen(year),
                                 'ultima_deteccion': point.fecha.isoformat(), 'semana_parcial': True, 'vigente': True}
                alert.notificacion = ('pendiente_revision' if alert.revision_manual else 'pendiente') if alert.nivel == 'critica' else ('panel' if alert.nivel == 'alta' else 'dashboard')
    active_alerts = db.scalars(select(Alerta).where(Alerta.fecha >= start, Alerta.fecha <= now,
                                                  Alerta.estado.in_(['nueva', 'en_revision']))).all()
    for alert in active_alerts:
        if alert.clave not in triggered:
            alert.revision_manual = True
            alert.notificacion = 'sin_evidencia_actual'
            alert.detalle = {**alert.detalle, 'vigente': False}
            prefix = 'Revisar: la señal ya no satisface la regla con los datos actuales. '
            if not alert.descripcion.startswith(prefix):
                alert.descripcion = prefix + alert.descripcion
    db.flush()
    return {'estado': 'ok', 'unidades': len(units), 'nuevas_alertas': created, 'anios_base': years}


def notificar_pendientes(db):
    settings = get_settings()
    if not settings.notifications_enabled:
        return 0
    token = settings.telegram_bot_token.get_secret_value()
    if not token or not settings.telegram_chat_id:
        return 0
    alerts = db.scalars(select(Alerta).where(Alerta.nivel == 'critica', Alerta.notificada.is_(False),
                        Alerta.revision_manual.is_(False), Alerta.estado.in_(['nueva', 'en_revision']))
                        .with_for_update(skip_locked=True)).all()
    sent = 0
    for alert in alerts:
        last = alert.detalle.get('ultima_deteccion')
        if not last or datetime.fromisoformat(last) < datetime.now(timezone.utc) - timedelta(hours=24):
            alert.notificacion = 'caducada'
            continue
        try:
            response = httpx.post(f'https://api.telegram.org/bot{token}/sendMessage',
                                  json={'chat_id': settings.telegram_chat_id,
                                        'text': f'Tunari · señal satelital #{alert.id}\n{alert.descripcion}\nRequiere verificación en terreno.'}, timeout=15)
            response.raise_for_status()
            if not response.json().get('ok'):
                raise ValueError('Respuesta Telegram inválida')
            alert.notificada, alert.notificacion = True, 'telegram'
            sent += 1
        except (httpx.HTTPError, ValueError):
            alert.notificacion = 'error_reintentable'
    return sent
