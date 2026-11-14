"""Importación acotada de archivos anuales públicos NASA; solo guarda el bbox local."""
import argparse
import csv
import hashlib
import io
import json
import sys
from datetime import date
from pathlib import Path

import httpx
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import get_settings
from app.database import SessionLocal, init_db
from app.models import Ingesta
from app.services.ingest_service import ingerir

CATALOG = 'https://firms.modaps.eosdis.nasa.gov/data/country/yearly_summary_files.txt'
BASE = 'https://firms.modaps.eosdis.nasa.gov/data/country/modis'


def descargar(desde, hasta, max_mb=60):
    if not 2001 <= desde <= hasta < date.today().year or hasta - desde > 4:
        raise ValueError('Selecciona entre 1 y 5 años completos desde 2001')
    settings = get_settings()
    west, south, east, north = map(float, settings.bbox.split(','))
    folder = settings.data_dir / 'raw/historico'
    folder.mkdir(parents=True, exist_ok=True)
    init_db()
    used = 0
    with httpx.Client(timeout=httpx.Timeout(40, connect=10), follow_redirects=True) as client:
        response = client.get(CATALOG)
        response.raise_for_status()
        catalog = {r[0]: int(r[1]) for r in csv.reader(io.StringIO(response.text)) if len(r) == 3 and r[1].isdigit()}
        for year in range(desde, hasta + 1):
            name = f'modis_{year}_Bolivia.csv'
            if name not in catalog:
                raise ValueError(f'NASA no publica {name} en su catálogo')
            url = f'{BASE}/{year}/{name}'
            key = 'annual:' + hashlib.sha256(f'{url}|{settings.bbox}'.encode()).hexdigest()
            with SessionLocal() as db:
                if db.scalar(select(Ingesta.id).where(Ingesta.clave == key, Ingesta.estado == 'ok')):
                    print(json.dumps({'anio': year, 'estado': 'ya_importado'}), flush=True)
                    continue
            if used + catalog[name] > max_mb * 1024 * 1024:
                raise ValueError(f'Límite total de {max_mb} MB; no se inicia {year}')
            selected, lines, transferred = [], 0, 0
            with client.stream('GET', url) as stream:
                stream.raise_for_status()
                def bounded_lines():
                    nonlocal transferred
                    for line in stream.iter_lines():
                        transferred += len(line.encode('utf-8')) + 1
                        if used + transferred > max_mb * 1024 * 1024:
                            raise ValueError('Descarga interrumpida por límite de bytes; no se importa el año incompleto')
                        yield line
                reader = csv.DictReader(bounded_lines())
                required = {'latitude', 'longitude', 'acq_date', 'acq_time', 'confidence'}
                if not required <= set(reader.fieldnames or []):
                    raise ValueError('Cabecera NASA inválida')
                for row in reader:
                    lines += 1
                    lon, lat = float(row['longitude']), float(row['latitude'])
                    if west <= lon <= east and south <= lat <= north:
                        selected.append(row)
                fields = reader.fieldnames
            used += transferred
            output = io.StringIO(newline='')
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            writer.writerows(selected)
            content = output.getvalue()
            digest = hashlib.sha256(content.encode()).hexdigest()
            local = folder / f'modis_{year}_cochabamba.csv'
            local.write_text(content, encoding='utf-8', newline='')
            detail = {'url': url, 'catalogo': CATALOG, 'bbox': settings.bbox,
                      'sha256_csv_local': digest, 'filas_pais': lines, 'filas_bbox': len(selected),
                      'bytes_descargados': transferred, 'cobertura': 'Archivo anual MODIS; no implica ausencia de fuego ni cobertura VIIRS.'}
            with SessionLocal.begin() as db:
                stats = ingerir(db, selected, 'MODIS_SP', 'historico', (date(year, 1, 1), date(year, 12, 31)))
                db.add(Ingesta(clave=key, fuente='MODIS_SP', origen='historico', inicio=date(year, 1, 1),
                              fin=date(year, 12, 31), completa=True, filas=len(selected), detalle=detail))
            local.with_suffix('.json').write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps({'anio': year, 'bytes': transferred, **stats}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--desde', type=int, default=date.today().year - 1)
    parser.add_argument('--hasta', type=int, default=date.today().year - 1)
    parser.add_argument('--max-mb', type=int, default=60)
    args = parser.parse_args()
    try:
        descargar(args.desde, args.hasta, args.max_mb)
    except (ValueError, OSError, httpx.HTTPError) as error:
        raise SystemExit(f'Importación detenida: {type(error).__name__}: {error}') from None
