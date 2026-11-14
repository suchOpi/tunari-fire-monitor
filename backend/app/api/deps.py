import hmac
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from fastapi import Depends, Header, HTTPException, Query
from ..database import SessionLocal
from ..config import get_settings

TZ = ZoneInfo('America/La_Paz')


def get_db():
    if not get_settings().database_enabled:
        raise HTTPException(503, 'PostGIS no está habilitado; el monitoreo NRT de lectura sigue disponible')
    with SessionLocal() as db:
        yield db


def require_token(authorization: str | None = Header(default=None), x_api_token: str | None = Header(default=None)):
    """Protege las rutas que modifican datos con un token de operador (API_TOKEN)."""
    expected = get_settings().api_token.get_secret_value()
    if not expected:
        raise HTTPException(503, 'Escritura deshabilitada: configura API_TOKEN en el servidor')
    bearer = authorization[7:] if authorization and authorization.lower().startswith('bearer ') else ''
    supplied = x_api_token or bearer
    if not hmac.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(401, 'Token de operador inválido o ausente', headers={'WWW-Authenticate': 'Bearer'})


class Filtros:
    def __init__(self, dias: int = Query(7, ge=1, le=366), distrito: int | None = Query(None, ge=1, le=15),
                 desde: date | None = None, hasta: date | None = None):
        end = hasta or datetime.now(TZ).date()
        start = desde or end - timedelta(days=dias - 1)
        if start > end:
            raise HTTPException(422, 'desde debe ser anterior o igual a hasta')
        self.inicio = datetime.combine(start, time.min, TZ)
        self.fin = datetime.combine(end + timedelta(days=1), time.min, TZ)
        self.distrito = distrito

    def aplicar(self, query, model, date_column):
        query = query.where(date_column >= self.inicio, date_column < self.fin)
        return query.where(model.distrito == self.distrito) if self.distrito else query


def paginar(db, query, schema, limit):
    from sqlalchemy import select, func
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows = db.scalars(query.limit(limit)).all()
    return {'items': [schema.model_validate(row) for row in rows], 'total': total, 'truncado': total > limit}
