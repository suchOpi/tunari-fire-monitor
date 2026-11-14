from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import get_settings


class Base(DeclarativeBase):
    pass


engine = create_engine(get_settings().database_url, pool_pre_ping=True, connect_args={'connect_timeout': 5})
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def init_db():
    from . import models                                                 
    with engine.begin() as connection:
        connection.execute(text('CREATE EXTENSION IF NOT EXISTS postgis'))
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        for column in ('producto VARCHAR(40)', 'brightness_k FLOAT', 'confidence_score FLOAT',
                       'posible_oclusion BOOLEAN NOT NULL DEFAULT false'):
            connection.execute(text(f'ALTER TABLE detecciones_raw ADD COLUMN IF NOT EXISTS {column}'))
        connection.execute(text('ALTER TABLE ingestas ADD COLUMN IF NOT EXISTS detalle JSON'))
        connection.execute(text("UPDATE detecciones_raw SET producto=fuente WHERE producto IS NULL AND (fuente LIKE '%_NRT' OR fuente LIKE '%_SP')"))
        connection.execute(text("UPDATE detecciones_raw SET fuente='nasa_mapkey' WHERE origen='nrt' AND fuente=producto"))
