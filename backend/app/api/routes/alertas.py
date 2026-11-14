from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from ..deps import get_db, require_token, Filtros, paginar
from ...models import Alerta
from ...schemas.alerta import AlertaOut, AlertaCambio

router = APIRouter(prefix='/alertas', tags=['alertas'])


def listar_array(filtros: Filtros = Depends(), limit: int = Query(1000, ge=1, le=5000), db=Depends(get_db)):
    return listar(filtros=filtros, estado=None, limit=limit, db=db)['items']


@router.get('')
def listar(filtros: Filtros = Depends(), estado: Literal['nueva', 'en_revision', 'atendida', 'falsa_alarma'] | None = None,
           limit: int = Query(1000, ge=1, le=5000), db=Depends(get_db)):
    query = filtros.aplicar(select(Alerta), Alerta, Alerta.fecha)
    if estado:
        query = query.where(Alerta.estado == estado)
    return paginar(db, query.order_by(Alerta.fecha.desc(), Alerta.id.desc()), AlertaOut, limit)


@router.patch('/{alerta_id}', response_model=AlertaOut, dependencies=[Depends(require_token)])
def actualizar(alerta_id: int, change: AlertaCambio, db=Depends(get_db)):
    alert = db.get(Alerta, alerta_id)
    if not alert:
        raise HTTPException(404, 'Alerta no encontrada')
    alert.estado, alert.actualizada = change.estado, datetime.now(timezone.utc)
    db.commit()
    return alert


@router.post('/{alerta_id}/confirmar', response_model=AlertaOut, dependencies=[Depends(require_token)])
def confirmar(alerta_id: int, db=Depends(get_db)):
    alert = db.get(Alerta, alerta_id)
    if not alert:
        raise HTTPException(404, 'Alerta no encontrada')
    if alert.estado in {'atendida', 'falsa_alarma'}:
        raise HTTPException(409, 'Reabre la alerta antes de confirmar la detección')
    if alert.detalle.get('vigente') is False:
        raise HTTPException(409, 'La señal no tiene evidencia actual; reevalúa los datos antes de confirmar')
    alert.revision_manual, alert.estado = False, 'en_revision'
    alert.actualizada = datetime.now(timezone.utc)
    alert.notificacion = 'pendiente' if alert.nivel == 'critica' else 'panel'
    db.commit()
    return alert
