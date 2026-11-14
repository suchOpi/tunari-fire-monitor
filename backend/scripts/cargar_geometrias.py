import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shapely.geometry import shape
from geoalchemy2.shape import from_shape
from sqlalchemy import select, text
from app.config import get_settings
from app.database import SessionLocal, init_db
from app.models import UnidadEspacial, Deteccion
from app.services.armonizacion import localizar, recalcular_evento, agrupar


def cargar(db, path, verified=False):
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    count = 0
    for feature in data['features']:
        props = feature['properties']
        if verified and props.get('demo', False):
            raise ValueError('No se puede verificar una geometría de demostración')
        category = props.get('clase', 'tunari' if path.stem == 'tunari' else 'distrito')
        if category not in {'tunari', 'distrito', 'industrial', 'asentamiento', 'cercado', 'periurbano'}:
            raise ValueError('Clase geográfica desconocida')
        district = props.get('distrito')
        if category == 'distrito' and (not isinstance(district, int) or not 1 <= district <= 15):
            raise ValueError('Cada distrito debe tener un entero 1–15')
        geometry = shape(feature['geometry'])
        if geometry.is_empty or not geometry.is_valid:
            raise ValueError('Geometría vacía o inválida')
        if category != 'asentamiento' and geometry.geom_type not in {'Polygon', 'MultiPolygon'}:
            raise ValueError('Se requiere Polygon o MultiPolygon')
        west, south, east, north = geometry.bounds
        if not (-180 <= west <= east <= 180 and -90 <= south <= north <= 90):
            raise ValueError('Se requieren coordenadas WGS84 (EPSG:4326)')
        key = str(props.get('id') or f'{category}:{district or count}')
        unit = db.get(UnidadEspacial, key) or UnidadEspacial(id=key)
        unit.clase, unit.distrito = category, district
        unit.nombre = props.get('nombre', key)
        unit.subdistrito = props.get('subdistrito')
        unit.verificada, unit.propiedades, unit.geom = verified, props, from_shape(geometry, srid=4326)
        db.add(unit)
        count += 1
    db.flush()
    return count


def main():
    parser = argparse.ArgumentParser(description='Importa GeoJSON WGS84. Solo --verificadas habilita clasificación y alertas espaciales.')
    parser.add_argument('archivos', nargs='*', type=Path)
    parser.add_argument('--verificadas', action='store_true')
    args = parser.parse_args()
    paths = args.archivos or [get_settings().data_dir / 'geo' / f for f in ('tunari.geojson', 'distritos_cochabamba.geojson')]
    init_db()
    with SessionLocal.begin() as db:
        db.execute(text('SELECT pg_advisory_xact_lock(734201)'))
        total = sum(cargar(db, path, args.verificadas) for path in paths)
        events = set()
        for detection in db.scalars(select(Deteccion)):
            fields = localizar(db, detection.longitude, detection.latitude)
            industrial = fields.pop('industrial')
            for key, value in fields.items():
                setattr(detection, key, value)
            detection.descartada = detection.tipo in {1, 2, 3} or industrial
            if detection.evento_id:
                events.add(detection.evento_id)
            elif not detection.descartada:
                agrupar(db, detection)
        db.flush()
        for event_id in events:
            recalcular_evento(db, event_id)
        print(f'{total} geometrías cargadas; verificadas={args.verificadas}. Reevalúa anomalías después de la carga.')


if __name__ == '__main__':
    main()
