from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, Float, Boolean, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class Alerta(Base):
    __tablename__ = 'alertas'
    id: Mapped[int] = mapped_column(primary_key=True)
    clave: Mapped[str] = mapped_column(String(180), unique=True)
    unidad_id: Mapped[str] = mapped_column(String(100), index=True)
    evento_id: Mapped[int | None] = mapped_column(ForeignKey('eventos_incendio.id', ondelete='SET NULL'))
    nivel: Mapped[str] = mapped_column(String(12), index=True)
    senal: Mapped[str] = mapped_column(String(40))
    descripcion: Mapped[str] = mapped_column(String(1500))
    estado: Mapped[str] = mapped_column(String(20), default='nueva', index=True)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    actualizada: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    distrito: Mapped[int | None] = mapped_column(Integer)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    revision_manual: Mapped[bool] = mapped_column(Boolean, default=True)
    notificacion: Mapped[str] = mapped_column(String(30), default='panel')
    notificada: Mapped[bool] = mapped_column(Boolean, default=False)
    detalle: Mapped[dict] = mapped_column(JSON, default=dict)


class EvaluacionUnidad(Base):
    __tablename__ = 'evaluaciones_unidad'
    clave: Mapped[str] = mapped_column(String(180), primary_key=True)
    unidad_id: Mapped[str] = mapped_column(String(100), index=True)
    semana: Mapped[int] = mapped_column(Integer)
    anio: Mapped[int] = mapped_column(Integer)
    regimen: Mapped[str] = mapped_column(String(20))
    posible_oclusion: Mapped[bool] = mapped_column(Boolean, default=False)
    cobertura_suficiente: Mapped[bool] = mapped_column(Boolean, default=False)
    climatologia: Mapped[dict] = mapped_column(JSON, default=dict)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
