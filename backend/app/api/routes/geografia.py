from datetime import datetime, timezone
from ...services.monitoring_state import operational_state
import json
from functools import lru_cache
from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import FileResponse
from typing import Literal
from sqlalchemy import select, func, distinct, text, or_
from ..deps import get_db
from ...database import SessionLocal
from ...models import Alerta, Deteccion, Evento
from ...schemas.alerta import AlertaOut
from ...services.cartografia import metadata_cache
from ...config import get_settings

router = APIRouter()
ACTIVE = ('nueva', 'en_revision')


@router.get('/territorio')
def territorio(db=Depends(get_db)):
    rows = db.execute(text("""SELECT id,nombre,clase,propiedades,ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom,0.0005)) AS geometry
        FROM unidades_espaciales WHERE verificada AND clase IN ('cercado','periurbano') ORDER BY id""")).mappings()
    return {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'geometry': json.loads(r['geometry']),
            'properties': {'id': r['id'], 'nombre': r['nombre'], 'clase': r['clase'], 'verificada': True, **(r['propiedades'] or {})}} for r in rows],
            'cartografia': metadata_cache(), 'postgis': 'conectado'}


@router.get('/cartografia/{capa}.png')
def imagen(capa: Literal['distritos','periurbanos']):
    path = get_settings().data_dir / 'geo/gamc' / f'{capa}.png'
    if not path.is_file():
        raise HTTPException(404, 'No existe una copia cartográfica local')
    return FileResponse(path, media_type='image/png', headers={'Cache-Control': 'public, max-age=86400'})


def cargar_geometrias(db):
    rows = db.execute(text("""
        WITH shapes AS (
            SELECT u.*, ST_Simplify(u.geom,0.0005) AS simple
            FROM unidades_espaciales u WHERE clase IN ('distrito','tunari')
        )
        SELECT u.id,u.nombre,u.clase,u.distrito,u.verificada,u.propiedades,
               ST_AsGeoJSON(CASE WHEN ST_IsValid(u.simple) AND NOT ST_IsEmpty(u.simple)
                            THEN u.simple ELSE u.geom END) AS geometry,
               ST_Area(u.geom::geography)/1e6 AS area_km2,
               EXISTS(SELECT 1 FROM unidades_espaciales p WHERE p.clase='tunari'
                      AND ST_Intersects(u.geom,p.geom)) AS en_pnt,
               (SELECT count(*) FROM unidades_espaciales d WHERE d.clase='distrito'
                AND ST_Intersects(u.geom,d.geom)) AS distritos_que_cruza
        FROM shapes u ORDER BY u.clase,u.distrito,u.id
    """)).mappings()
    result = {'distritos': [], 'pnt': []}
    for row in rows:
        props = row['propiedades'] or {}
        properties = {'id': row['distrito'] if row['clase'] == 'distrito' else row['id'],
                      'unidad_id': row['id'], 'nombre': row['nombre'], 'area_km2': round(row['area_km2'], 3),
                      'en_pnt': row['en_pnt'], 'distritos_que_cruza': row['distritos_que_cruza'],
                      'verificada': row['verificada'], 'ilustrativa': bool(props.get('demo')),
                      'poblacion_aproximada': props.get('poblacion_aproximada', props.get('poblacion'))}
        result['distritos' if row['clase'] == 'distrito' else 'pnt'].append({
            'type': 'Feature', 'id': properties['id'], 'geometry': json.loads(row['geometry']), 'properties': properties})
    return result


@lru_cache(maxsize=1)
def geometrias_cache():
    with SessionLocal() as db:
        return cargar_geometrias(db)


def historicos():
    return select(Deteccion.evento_id).where(Deteccion.origen == 'historico', Deteccion.descartada.is_(False))


def distritos_collection(db):
    ready = operational_state(db, get_settings(), datetime.now(timezone.utc))['motor_alertas']['disponible']
    alerts = dict(db.execute(select(Alerta.distrito, func.count()).where(Alerta.estado.in_(ACTIVE)).group_by(Alerta.distrito)).all())
    events = dict(db.execute(select(Evento.distrito, func.count(distinct(Evento.id)))
                            .where(Evento.id.in_(historicos())).group_by(Evento.distrito)).all())
    return {'type': 'FeatureCollection', 'features': [
        {**feature, 'properties': {**feature['properties'], 'alertas_activas': alerts.get(feature['id'], 0) if ready else None,
                                  'eventos_historicos': events.get(feature['id'], 0)}}
        for feature in geometrias_cache()['distritos']]}


@router.get('/distritos')
def distritos(db=Depends(get_db)):
    return distritos_collection(db)


@router.get('/pnt')
def pnt(db=Depends(get_db)):
    ready = operational_state(db, get_settings(), datetime.now(timezone.utc))['motor_alertas']['disponible']
    features = []
    for feature in geometrias_cache()['pnt']:
        count = db.scalar(select(func.count()).select_from(Alerta).where(
            Alerta.estado.in_(ACTIVE), or_(Alerta.unidad_id == feature['properties']['unidad_id'],
                                         Alerta.evento_id.in_(select(Evento.id).where(Evento.en_tunari.is_(True))))))
        features.append({**feature, 'properties': {**feature['properties'], 'alertas_activas': count if ready else None}})
    return {'type': 'FeatureCollection', 'features': features}


@router.get('/distrito/{id}')
def distrito(id: int = Path(ge=1, le=15), db=Depends(get_db)):
    feature = next((f for f in distritos_collection(db)['features'] if f['id'] == id), None)
    if feature is None:
        raise HTTPException(404, 'Distrito no disponible')
    year = func.extract('year', func.timezone('America/La_Paz', Evento.inicio))
    years = db.execute(select(year, func.count()).where(Evento.distrito == id, Evento.id.in_(historicos()))
                       .group_by(year).order_by(year)).all()
    detections = (Deteccion.distrito == id, Deteccion.descartada.is_(False))
    frp, samples = db.execute(select(func.avg(Deteccion.frp), func.count(Deteccion.frp)).where(*detections)).one()
    sensors = db.scalars(select(distinct(Deteccion.sensor)).where(*detections).order_by(Deteccion.sensor)).all()
    active = db.scalars(select(Alerta).where(Alerta.distrito == id, Alerta.estado.in_(ACTIVE)).order_by(Alerta.fecha.desc())).all()
    return {**feature, 'estadisticas': {
        'eventos_por_anio': [{'anio': int(y), 'eventos': n} for y, n in years],
        'alertas_activas': [AlertaOut.model_validate(a).model_dump(mode='json') for a in active],
        'frp_promedio': frp, 'mediciones_frp': samples, 'sensores': list(sensors),
        'alcance': 'Registros con distrito asignado; no se reasignan focos con límites ilustrativos.'}}
