from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict


class AlertaCambio(BaseModel):
    estado: Literal['nueva', 'en_revision', 'atendida', 'falsa_alarma']


class AlertaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    unidad_id: str
    evento_id: int | None
    nivel: str
    senal: str
    descripcion: str
    estado: str
    fecha: datetime
    distrito: int | None
    latitude: float
    longitude: float
    revision_manual: bool
    notificacion: str
