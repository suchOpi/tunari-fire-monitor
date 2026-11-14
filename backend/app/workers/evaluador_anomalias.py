import logging
from datetime import datetime, timezone
from ..database import SessionLocal, init_db
from ..services.alertas_service import evaluar_actualizacion, notificar_pendientes
from ..services.monitoring_state import registrar


def ejecutar():
    now = datetime.now(timezone.utc)
    try:
        with SessionLocal.begin() as db:
            result = evaluar_actualizacion(db, now)
            registrar(db, 'evaluador:last_attempt', now, result['estado'], result)
            if result['estado'] == 'ok':
                registrar(db, 'evaluador:last_success', now, 'ok', result)
        result['notificaciones'] = 0
        if result['estado'] == 'ok':
            with SessionLocal.begin() as db:
                result['notificaciones'] = notificar_pendientes(db)
        return result
    except Exception as error:
        with SessionLocal.begin() as db:
            registrar(db, 'evaluador:last_attempt', now, 'error', {'error': type(error).__name__})
        raise


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    init_db()
    logging.info('%s', ejecutar())
