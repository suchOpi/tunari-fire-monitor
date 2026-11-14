from datetime import date, datetime, time, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, distinct
from ..deps import get_db, Filtros, TZ
from ...models import Deteccion, Evento, Alerta, Ingesta, EvaluacionUnidad, UnidadEspacial
from ...services.anomalias import regimen
from ...services.alertas_service import AVAILABLE
from ...config import get_settings
from ...services.monitoring_state import operational_state, apply_availability

router = APIRouter(prefix='/estadisticas', tags=['estadisticas'])


def cobertura_anual(year, ingestas, current_year):
    if year >= current_year:
        return False
    start, end = date(year, 1, 1), date(year, 12, 31)
    return all(any(i.completa and i.estado == 'ok' and i.fuente.removesuffix('_SP') == source
                   and i.inicio <= max(start, since) and i.fin >= end for i in ingestas)
               for source, since in AVAILABLE.items() if since <= end)


@router.get('')
def resumen(filtros: Filtros = Depends(), db=Depends(get_db)):
    return resumen_db(filtros, db)


def resumen_db(filtros, db, now=None, settings=None):
    local = now.astimezone(TZ) if now else datetime.now(TZ)
    settings = settings or get_settings()
    today = datetime.combine(local.date(), time.min, TZ)
    raw = select(func.count(Deteccion.id)).where(Deteccion.descartada.is_(False), Deteccion.fecha >= today,
                                                Deteccion.fecha < today + timedelta(days=1))
    active = filtros.aplicar(select(func.count(Alerta.id)).where(Alerta.estado.in_(['nueva', 'en_revision'])), Alerta, Alerta.fecha)
    history = select(func.count(distinct(Deteccion.evento_id))).where(Deteccion.origen == 'historico', Deteccion.descartada.is_(False))
    if filtros.distrito:
        raw = raw.where(Deteccion.distrito == filtros.distrito)
        history = history.where(Deteccion.distrito == filtros.distrito)
    year_column = func.extract('year', func.timezone('America/La_Paz', Deteccion.fecha))
    series_query = select(year_column, func.count(distinct(Deteccion.evento_id))).where(
        Deteccion.origen == 'historico', Deteccion.descartada.is_(False))
    if filtros.distrito:
        series_query = series_query.where(Deteccion.distrito == filtros.distrito)
    counts = {int(year): count for year, count in db.execute(series_query.group_by(year_column))}
    ingestas = db.scalars(select(Ingesta).where(Ingesta.origen == 'historico')).all()
    serie = [{'anio': year, 'eventos': counts.get(year, 0 if cobertura_anual(year, ingestas, local.year) else None), 'regimen': regimen(year),
              'cobertura': 'completa' if cobertura_anual(year, ingestas, local.year) else ('parcial' if any(i.inicio.year <= year <= i.fin.year for i in ingestas) else 'sin_datos')}
             for year in range(2000, local.year + 1)]
    current_year, week, _ = local.isocalendar()
    eval_query = select(EvaluacionUnidad).where(EvaluacionUnidad.anio == current_year, EvaluacionUnidad.semana == week)
    if filtros.distrito:
        eval_query = eval_query.where(EvaluacionUnidad.unidad_id == f'distrito:{filtros.distrito}')
    evaluations = db.scalars(eval_query).all()
    latest = db.scalars(select(Ingesta).where(Ingesta.origen == 'nrt').order_by(Ingesta.fecha.desc()).limit(100)).all()
    sources = {}
    for item in latest:
        if item.fuente not in sources:
            sources[item.fuente] = {**(item.detalle or {}), 'estado': item.estado, 'fecha': item.fecha.isoformat()}
    geo_count = db.scalar(select(func.count()).select_from(UnidadEspacial).where(UnidadEspacial.verificada.is_(True)))
    tunari_verified = db.scalar(select(UnidadEspacial.id).where(UnidadEspacial.verificada.is_(True), UnidadEspacial.clase == 'tunari').limit(1)) is not None
    result = dict(detecciones_hoy=db.scalar(raw), alertas_activas=db.scalar(active), eventos_historicos=db.scalar(history),
                serie=serie, posible_oclusion=sum(e.posible_oclusion for e in evaluations),
                climatologia_disponible=any(e.cobertura_suficiente for e in evaluations),
                ultima_ingesta=latest[0].fecha.isoformat() if latest else None, fuentes=sources,
                geometrias_verificadas=geo_count, tunari_verificado=tunari_verified, nota='2012 es el cambio de régimen; la flota también cambia en 2018 y 2023. Sin detecciones no significa sin fuego.')
    operation = operational_state(db, settings, local)
    verified = not filtros.distrito or db.scalar(select(UnidadEspacial.id).where(UnidadEspacial.clase == 'distrito', UnidadEspacial.distrito == filtros.distrito, UnidadEspacial.verificada.is_(True)).limit(1)) is not None
    result.update(fuentes=operation['fuentes'], ultima_ingesta=operation['ultima_ingesta'], monitoreo=operation)
    return apply_availability(result, operation, verified)
