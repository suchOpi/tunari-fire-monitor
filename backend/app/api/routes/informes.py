import csv
import io
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Literal
from fastapi import APIRouter, Depends, Query, Response, HTTPException
from ..deps import get_db
from ...services.informes import informe

router = APIRouter(prefix='/informes', tags=['informes e IA local'])


@router.get('/historico')
def historico(desde: int | None = Query(default=None, ge=2000),
              hasta: int | None = Query(default=None, ge=2000),
              distrito: int | None = Query(default=None, ge=1, le=15),
              ambito: Literal['cercado', 'entorno'] = 'cercado',
              formato: Literal['json', 'csv', 'informe'] = 'json',
              sensor: Literal['MODIS', 'VIIRS_NOAA20', 'VIIRS_NOAA21', 'VIIRS_SNPP'] = 'MODIS', db=Depends(get_db)):
    current = datetime.now(ZoneInfo('America/La_Paz')).year
    desde, hasta = desde if desde is not None else current - 1, hasta if hasta is not None else current
    if desde > hasta or hasta > current or hasta - desde > 25:
        raise HTTPException(422, 'Selecciona hasta 26 años, incluyendo como máximo el año actual')
    result = informe(db, desde, hasta, distrito, ambito, sensor=sensor)
    if formato == 'json':
        return result
    filename = f'tunari-{ambito}-{sensor}-{desde}-{hasta}'
    if formato == 'informe':
        return Response(json.dumps(result, ensure_ascii=False, indent=2), media_type='application/json',
                        headers={'Content-Disposition': f'attachment; filename="{filename}.json"'})
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(['mes', 'eventos_' + sensor, 'ambito', 'distrito', 'cobertura', 'dias_cubiertos', 'nota'])
    for item in result['calendario']:
        writer.writerow([item['mes'], item['eventos'], result['ambito_descripcion'], distrito or 'todos',
                         item['cobertura'], item['dias_cubiertos'],
                         'No equivale a incendios confirmados; vacio significa sin dato o periodo futuro; NRT provisional'])
    return Response('\ufeff' + output.getvalue(), media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition': f'attachment; filename="{filename}.csv"'})
