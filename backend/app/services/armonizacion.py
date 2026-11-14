from datetime import timedelta
from sqlalchemy import select, func, cast
from geoalchemy2 import Geography
from ..models import Deteccion, Evento, UnidadEspacial


def localizar(db, lon: float, lat: float):
    point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
    x, y = db.execute(select(func.ST_X(func.ST_Transform(point, 32719)),
                             func.ST_Y(func.ST_Transform(point, 32719)))).one()
    zones = db.scalars(select(UnidadEspacial).where(
        UnidadEspacial.verificada.is_(True), func.ST_Covers(UnidadEspacial.geom, point)
    ).order_by(UnidadEspacial.id)).all()
    district = next((z for z in zones if z.clase == 'distrito'), None)
    settlement = db.scalar(select(UnidadEspacial.id).where(
        UnidadEspacial.verificada.is_(True), UnidadEspacial.clase.in_(['asentamiento', 'periurbano']),
        func.ST_DWithin(cast(UnidadEspacial.geom, Geography), cast(point, Geography), 2000)
    ).limit(1))
    return dict(hex_id=f'utm19s:{int(x // 1000)}:{int(y // 1000)}',
                en_tunari=any(z.clase == 'tunari' for z in zones),
                cerca_asentamiento=settlement is not None,
                distrito=district.distrito if district else None,
                subdistrito=district.subdistrito if district else None,
                industrial=any(z.clase == 'industrial' for z in zones))


def recalcular_evento(db, evento_id: int):
    event = db.get(Evento, evento_id)
    points = db.scalars(select(Deteccion).where(
        Deteccion.evento_id == evento_id, Deteccion.descartada.is_(False))).all()
    if not points:
        db.delete(event)
        db.flush()
        return
    event.inicio, event.fin = min(d.fecha for d in points), max(d.fecha for d in points)
    event.sensores_presentes = sorted({d.sensor for d in points})
    event.sensor_principal = 'VIIRS' if 'VIIRS' in event.sensores_presentes else 'MODIS'
    frps = [d.frp for d in points if d.frp is not None]
    event.frp_medio = sum(frps) / len(frps) if frps else None
    event.frp_max = max(frps) if frps else None
    event.num_detecciones = len(points)
    anchor = localizar(db, event.longitude, event.latitude)
    event.distrito, event.subdistrito, event.hex_id = anchor['distrito'], anchor['subdistrito'], anchor['hex_id']
    event.en_tunari = any(d.en_tunari for d in points)
    event.cerca_asentamiento = any(d.cerca_asentamiento for d in points)
    event.candidata = all(d.candidata for d in points)


def agrupar(db, detection: Deteccion):
    previous_id = detection.evento_id
    if detection.descartada:
        detection.evento_id = None
        db.flush()
        if previous_id:
            recalcular_evento(db, previous_id)
        return
    if previous_id:
        recalcular_evento(db, previous_id)
        return
                                                                                     
    distance = func.ST_Distance(cast(Evento.geom, Geography), cast(detection.geom, Geography))
    event = db.scalar(select(Evento).where(
        Evento.referencia.between(detection.fecha - timedelta(hours=24), detection.fecha + timedelta(hours=24)),
        func.ST_DWithin(cast(Evento.geom, Geography), cast(detection.geom, Geography), 1500)
    ).order_by(distance, Evento.id).limit(1))
    if not event:
        event = Evento(referencia=detection.fecha, inicio=detection.fecha, fin=detection.fecha,
                       latitude=detection.latitude, longitude=detection.longitude, geom=detection.geom,
                       sensor_principal=detection.sensor, sensores_presentes=[detection.sensor],
                       en_tunari=detection.en_tunari, cerca_asentamiento=detection.cerca_asentamiento,
                       distrito=detection.distrito, subdistrito=detection.subdistrito,
                       hex_id=detection.hex_id, num_detecciones=0)
        db.add(event)
        db.flush()
    detection.evento_id = event.id
    db.flush()
    recalcular_evento(db, event.id)
