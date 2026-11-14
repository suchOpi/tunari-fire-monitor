from datetime import datetime
from sqlalchemy import String, DateTime, Float, Integer, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geometry
from ..database import Base


class Evento(Base):
    __tablename__ = 'eventos_incendio'
    id: Mapped[int] = mapped_column(primary_key=True)
    referencia: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    fin: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    geom = mapped_column(Geometry('POINT', srid=4326, spatial_index=True), nullable=False)
    sensor_principal: Mapped[str] = mapped_column(String(10))
    sensores_presentes: Mapped[list] = mapped_column(JSON, default=list)
    en_tunari: Mapped[bool] = mapped_column(Boolean, default=False)
    cerca_asentamiento: Mapped[bool] = mapped_column(Boolean, default=False)
    distrito: Mapped[int | None] = mapped_column(Integer, index=True)
    subdistrito: Mapped[str | None] = mapped_column(String(100))
    hex_id: Mapped[str] = mapped_column(String(60), index=True)
    frp_medio: Mapped[float | None] = mapped_column(Float)
    frp_max: Mapped[float | None] = mapped_column(Float)
    num_detecciones: Mapped[int] = mapped_column(Integer, default=0)
    candidata: Mapped[bool] = mapped_column(Boolean, default=True)
    posible_oclusion: Mapped[bool] = mapped_column(Boolean, default=False)
