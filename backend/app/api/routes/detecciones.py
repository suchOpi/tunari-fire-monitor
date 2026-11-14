from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from ..deps import get_db, Filtros, paginar
from ...models import Deteccion
from ...schemas.deteccion import DeteccionOut

router = APIRouter(prefix='/detecciones', tags=['detecciones'])


@router.get('')
def listar(filtros: Filtros = Depends(), limit: int = Query(5000, ge=1, le=20000), db=Depends(get_db)):
    query = filtros.aplicar(select(Deteccion).where(Deteccion.descartada.is_(False)), Deteccion, Deteccion.fecha)
    return paginar(db, query.order_by(Deteccion.fecha.desc(), Deteccion.id.desc()), DeteccionOut, limit)


@router.get('/recientes')
def recientes(filtros: Filtros = Depends(), limit: int = Query(5000, ge=1, le=20000), db=Depends(get_db)):
    query = filtros.aplicar(select(Deteccion).where(Deteccion.descartada.is_(False)), Deteccion, Deteccion.fecha)
    rows = db.scalars(query.order_by(Deteccion.fecha.desc(), Deteccion.id.desc()).limit(limit))
    result = []
    for row in rows:
        item = DeteccionOut.model_validate(row).model_dump(mode='json')
        item.update(sensor='MODIS' if row.sensor == 'MODIS' else (row.producto or row.fuente).removesuffix('_NRT').removesuffix('_SP'),
                    fuente=row.fuente, origen=row.origen)
        result.append(item)
    return result
