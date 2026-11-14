import math
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from ..deps import Filtros
from ...services import gamc_client, live_firms
from ...services.persistent_monitor import monitor as persistent_monitor
from ...config import get_settings
from ...database import SessionLocal

router = APIRouter(tags=['monitoreo real'])


@router.get('/monitoreo')
def monitoreo(filters: Filtros = Depends()):
    if get_settings().database_enabled:
        with SessionLocal() as db:
            return persistent_monitor(db, filters)
    if not get_settings().live_monitoring_enabled:
        raise HTTPException(503, 'No hay una fuente de monitoreo habilitada')
    return live_firms.monitor(filters)


@router.get('/capas')
def capas():
    return gamc_client.metadata()


@router.get('/gamc/wms')
def wms(request: Request, capa: Literal['distritos', 'periurbanos', 'cota2750']):
    incoming = {key.upper(): value for key, value in request.query_params.items()}
    operation = incoming.get('REQUEST', 'GetMap')
    if operation not in {'GetMap', 'GetLegendGraphic'}:
        raise HTTPException(422, 'Operación WMS no admitida; usa /gamc/consulta para atributos')
    params = {'SERVICE': 'WMS', 'VERSION': '1.1.1' if operation == 'GetMap' else '1.0.0',
              'REQUEST': operation, 'FORMAT': 'image/png', 'TRANSPARENT': 'true', 'LAYERS': ''}
    if operation == 'GetMap':
        try:
            bounds = list(map(float, incoming['BBOX'].split(',')))
            width, height = int(incoming['WIDTH']), int(incoming['HEIGHT'])
            srs = incoming.get('SRS', 'EPSG:3857')
            if len(bounds) != 4 or not all(map(math.isfinite, bounds)) or bounds[0] >= bounds[2] or bounds[1] >= bounds[3] or not (1 <= width <= 2048 and 1 <= height <= 2048) or srs not in {'EPSG:3857', 'EPSG:4326'}:
                raise ValueError()
        except (ValueError, KeyError):
            raise HTTPException(422, 'Parámetros de mapa inválidos') from None
        params.update(BBOX=incoming['BBOX'], WIDTH=str(width), HEIGHT=str(height), SRS=srs)
    try:
        response = gamc_client.fetch_wms(capa, params)
    except (RuntimeError, ValueError) as error:
        raise HTTPException(502, str(error)) from None
    if response is None:
        raise HTTPException(503, 'Cartografía GAMC temporalmente no disponible; los focos NASA siguen disponibles')
    return Response(response.content, media_type='image/png', headers={'Cache-Control': 'public, max-age=300'})


@router.get('/gamc/consulta')
def consulta(lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180),
             capa: Literal['distritos', 'periurbanos', 'cota2750'] = 'distritos'):
    try:
        result = gamc_client.feature_info(capa, lon, lat)
        return {'capa': capa, 'disponible': result is not None, 'atributos': result or []}
    except (RuntimeError, ValueError) as error:
        raise HTTPException(502, str(error)) from None
