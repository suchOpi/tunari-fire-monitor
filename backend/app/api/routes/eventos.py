from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from ..deps import get_db, Filtros, paginar
from ...models import Evento
from ...schemas.evento import EventoOut

router = APIRouter(prefix='/eventos', tags=['eventos'])


@router.get('')
def listar(filtros: Filtros = Depends(), limit: int = Query(5000, ge=1, le=20000), db=Depends(get_db)):
    query = select(Evento).where(Evento.fin >= filtros.inicio, Evento.inicio < filtros.fin)
    if filtros.distrito:
        query = query.where(Evento.distrito == filtros.distrito)
    return paginar(db, query.order_by(Evento.inicio.desc(), Evento.id.desc()), EventoOut, limit)
