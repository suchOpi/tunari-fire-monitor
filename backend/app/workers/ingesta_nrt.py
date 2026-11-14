import argparse
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, text
from ..config import get_settings
from ..database import SessionLocal, engine, init_db
from ..models import Ingesta
from ..services.firms_client import fetch_area, fetch_nrt_keyless
from ..services.ingest_service import ingerir
from ..services.monitoring_state import registrar, read_sources
from .evaluador_anomalias import ejecutar

log = logging.getLogger('tunari.worker')


def obtener_lotes(settings):
    if not settings.firms_map_key.get_secret_value():
        return 'nasa_keyless', fetch_nrt_keyless(settings.bbox)
    batches = {}
    for source in settings.firms_sources.split(','):
        source = source.strip()
        try:
            batches[source] = {'estado': 'ok', 'rows': fetch_area(source, settings.nrt_days), 'fuente_datos': 'nasa_mapkey'}
        except (RuntimeError, ValueError) as error:
            log.warning('NASA %s no disponible: %s', source, type(error).__name__)
            batches[source] = {'estado': 'error', 'rows': [], 'error': str(error), 'fuente_datos': 'nasa_mapkey'}
    return 'nasa_mapkey', batches


def ciclo(scheduled=False):
    settings = get_settings()
    if scheduled and not settings.nrt_scheduler_enabled:
        return {'estado': 'omitida', 'motivo': 'NRT_SCHEDULER_ENABLED=false'}
                                                                                           
    with engine.connect() as guard:
        if not guard.scalar(text('SELECT pg_try_advisory_lock(734202)')):
            return {'estado': 'omitida', 'motivo': 'Otra ingesta está en ejecución'}
        try:
            now = datetime.now(timezone.utc)
            with SessionLocal.begin() as db:
                if scheduled:
                    registrar(db, 'worker:last_scheduled', now, detalle={'intervalo_horas': settings.nrt_interval_hours})
                control = db.scalar(select(Ingesta).where(Ingesta.clave == 'worker:last_attempt'))
                tolerance = timedelta(seconds=60 if scheduled else 0)
                if control and now - control.fecha < timedelta(hours=settings.nrt_interval_hours) - tolerance:
                    return {'estado': 'omitida', 'motivo': 'Intervalo mínimo entre descargas aún no cumplido'}
                if not control:
                    control = Ingesta(clave='worker:last_attempt', fuente='worker', origen='control', inicio=now.date(), fin=now.date())
                    db.add(control)
                control.fecha = now
                control.estado = 'en_curso'
            provider, batches = obtener_lotes(settings)
            report = {'fecha': now.isoformat(), 'fuente_datos': provider, 'bbox': settings.bbox,
                      'programada': scheduled, 'fuentes': {}}
            start = (now - timedelta(hours=24)).date() if provider == 'nasa_keyless' else now.date() - timedelta(days=settings.nrt_days - 1)
            with SessionLocal.begin() as db:
                db.scalar(select(Ingesta).where(Ingesta.clave == 'worker:last_attempt')).detalle = {
                    'fuente_datos': provider, 'programada': scheduled}
            for source, batch in batches.items():
                key = f'nrt:{source}:{now.isoformat()}'
                detail = {k: v for k, v in batch.items() if k != 'rows'}
                count = 0
                try:
                    if batch['estado'] == 'ok':
                        with SessionLocal.begin() as db:
                            stats = ingerir(db, batch['rows'], source, provider=provider)
                        count = stats['nuevas']
                        detail.update(stats)
                except Exception as error:
                    detail.update(estado='error', error=type(error).__name__)
                    log.warning('%s: %s; sin registrar un cero de incendios', source, type(error).__name__)
                with SessionLocal.begin() as db:
                    db.add(Ingesta(clave=key, fuente=source, origen='nrt', inicio=start,
                                  fin=now.date(), completa=False, filas=count, fecha=now,
                                  estado=detail['estado'], detalle=detail))
                report['fuentes'][source] = detail
            finished = datetime.now(timezone.utc)
            with SessionLocal.begin() as db:
                sources = read_sources(db, settings, finished)
                complete = bool(sources) and all(s['estado'] == 'ok' for s in sources.values())
                report['estado'] = 'ok' if complete else 'parcial' if any(s['estado'] == 'ok' for s in sources.values()) else 'error'
                registrar(db, 'worker:last_attempt', now, report['estado'], {'programada': scheduled, 'finalizada': finished.isoformat()})
                if complete:
                    registrar(db, 'worker:last_success', finished)
            report['evaluacion'] = ejecutar()
            path = settings.data_dir / 'processed/ultima_ingesta_nrt.json'
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_suffix('.tmp')
            temp.write_text(json.dumps(report, ensure_ascii=False), encoding='utf-8')
            temp.replace(path)
            return report
        finally:
            guard.execute(text('SELECT pg_advisory_unlock(734202)'))


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--once', action='store_true', help='Ejecuta una sola ingesta (comportamiento por defecto)')
    mode.add_argument('--loop', action='store_true', help='Repite cada NRT_INTERVAL_HOURS; requiere activación explícita')
    parser.add_argument('--scheduled', action='store_true', help='Ejecución por el Programador de tareas local')
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s %(message)s')
    init_db()
    while True:
        try:
            result = ciclo(scheduled=True) if args.scheduled else ciclo()
            print(json.dumps(result, ensure_ascii=False))
        except Exception as error:
            log.warning('Ciclo fallido: %s', type(error).__name__)
            if not args.loop:
                return 1
        if not args.loop:
            return 2 if result and result.get('estado') in {'error', 'parcial'} else 0
        time.sleep(get_settings().nrt_interval_hours * 3600)


if __name__ == '__main__':
    raise SystemExit(main())
