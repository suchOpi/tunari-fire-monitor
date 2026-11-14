from datetime import datetime, date, timezone
from sqlalchemy import String, DateTime, Float, Integer, Boolean, ForeignKey, JSON, Date
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geometry
from ..database import Base


class Deteccion(Base):
    __tablename__ = 'detecciones_raw'
    id: Mapped[int] = mapped_column(primary_key=True)
    clave: Mapped[str] = mapped_column(String(64), unique=True)
    sensor: Mapped[str] = mapped_column(String(10), index=True)
    satelite: Mapped[str] = mapped_column(String(40))
    fuente: Mapped[str] = mapped_column(String(40))
    producto: Mapped[str | None] = mapped_column(String(40))
    origen: Mapped[str] = mapped_column(String(12))
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    geom = mapped_column(Geometry('POINT', srid=4326, spatial_index=True), nullable=False)
    resolucion: Mapped[int] = mapped_column(Integer)
    frp: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[str] = mapped_column(String(30))
    brightness: Mapped[float | None] = mapped_column(Float)
    bright_ti4: Mapped[float | None] = mapped_column(Float)
    brightness_k: Mapped[float | None] = mapped_column(Float)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    posible_oclusion: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    tipo: Mapped[int | None] = mapped_column(Integer)
    candidata: Mapped[bool] = mapped_column(Boolean, default=True)
    descartada: Mapped[bool] = mapped_column(Boolean, default=False)
    revision_manual: Mapped[bool] = mapped_column(Boolean, default=True)
    en_tunari: Mapped[bool] = mapped_column(Boolean, default=False)
    cerca_asentamiento: Mapped[bool] = mapped_column(Boolean, default=False)
    distrito: Mapped[int | None] = mapped_column(Integer, index=True)
    subdistrito: Mapped[str | None] = mapped_column(String(100))
    hex_id: Mapped[str] = mapped_column(String(60), index=True)
    evento_id: Mapped[int | None] = mapped_column(ForeignKey('eventos_incendio.id', ondelete='SET NULL'), index=True)
    original: Mapped[dict] = mapped_column(JSON)


class UnidadEspacial(Base):
    __tablename__ = 'unidades_espaciales'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    clase: Mapped[str] = mapped_column(String(25), index=True)
    nombre: Mapped[str] = mapped_column(String(150))
    distrito: Mapped[int | None] = mapped_column(Integer)
    subdistrito: Mapped[str | None] = mapped_column(String(100))
    verificada: Mapped[bool] = mapped_column(Boolean, default=False)
    geom = mapped_column(Geometry('GEOMETRY', srid=4326, spatial_index=True), nullable=False)
    propiedades: Mapped[dict] = mapped_column(JSON, default=dict)


class Ingesta(Base):
    __tablename__ = 'ingestas'
    id: Mapped[int] = mapped_column(primary_key=True)
    clave: Mapped[str] = mapped_column(String(100), unique=True)
    fuente: Mapped[str] = mapped_column(String(40))
    origen: Mapped[str] = mapped_column(String(12))
    inicio: Mapped[date] = mapped_column(Date)
    fin: Mapped[date] = mapped_column(Date)
    completa: Mapped[bool] = mapped_column(Boolean, default=False)
    filas: Mapped[int] = mapped_column(Integer, default=0)
    estado: Mapped[str] = mapped_column(String(20), default='ok')
    detalle: Mapped[dict | None] = mapped_column(JSON)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
