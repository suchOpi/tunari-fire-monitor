import argparse
import csv
import hashlib
import sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from app.database import SessionLocal, init_db
from app.models import Ingesta
from app.services.firms_client import SOURCES
from app.services.ingest_service import ingerir


def main():
    parser = argparse.ArgumentParser(description='Carga transaccional de CSV anual FIRMS; nunca usa la API de Área.')
    parser.add_argument('archivo', type=Path)
    parser.add_argument('--source', required=True, choices=sorted(SOURCES))
    parser.add_argument('--inicio', required=True, type=date.fromisoformat)
    parser.add_argument('--fin', required=True, type=date.fromisoformat)
    parser.add_argument('--completo', action='store_true', help='Certifica que el archivo incluye todo el período y el bbox, incluso semanas sin registros.')
    args = parser.parse_args()
    if args.inicio > args.fin or args.fin >= date.today() or args.inicio.year < 2000:
        parser.error('El período debe terminar antes de hoy y comenzar desde 2000')
    if args.completo and not args.source.endswith('_SP'):
        parser.error('La climatología exige archivos históricos estándar (_SP)')
    with args.archivo.open('rb') as handle:
        digest = hashlib.file_digest(handle, 'sha256').hexdigest()
    key = f'hist:{args.source}:{digest}'
    init_db()
    with SessionLocal.begin() as db:
        previous = db.scalar(select(Ingesta).where(Ingesta.clave == key))
        if previous:
            if previous.inicio != args.inicio or previous.fin != args.fin:
                parser.error('El archivo ya fue importado con otro período')
            previous.completa = previous.completa or args.completo
            print('Archivo ya importado; sin duplicados. Cobertura actualizada si corresponde.')
            return
        with args.archivo.open(encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle)
            if not {'latitude', 'longitude', 'acq_date', 'acq_time', 'confidence'} <= set(reader.fieldnames or []):
                parser.error('Cabecera CSV FIRMS inválida')
            stats = ingerir(db, reader, args.source, 'historico', (args.inicio, args.fin))
        db.add(Ingesta(clave=key, fuente=args.source, origen='historico', inicio=args.inicio,
                      fin=args.fin, completa=args.completo, filas=stats['leidas']))
        print(stats)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(str(error)) from None
