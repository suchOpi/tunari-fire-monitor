from fastapi import APIRouter
from sqlalchemy import text
from ...database import engine
from ...config import get_settings

router = APIRouter(tags=['sistema'])


@router.get('/salud')
def salud():
    settings = get_settings()
    version = None
    if settings.database_enabled:
        with engine.connect() as db:
            version = db.scalar(text('SELECT PostGIS_Version()'))
    has_key = bool(settings.firms_map_key.get_secret_value())
    return {'estado': 'ok', 'postgis': version, 'persistencia': settings.database_enabled,
            'firms_configurado': has_key,
            'nrt_publico': not has_key and (settings.database_enabled or settings.live_monitoring_enabled),
            'ingesta_programada': settings.nrt_scheduler_enabled}
