from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DeteccionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sensor: str
    fuente: str
    producto: str | None
    satelite: str
    fecha: datetime
    latitude: float
    longitude: float
    resolucion: int
    frp: float | None
    confidence: str
    brightness: float | None
    bright_ti4: float | None
    brightness_k: float | None
    confidence_score: float | None
    posible_oclusion: bool
    candidata: bool
    revision_manual: bool
    en_tunari: bool
    distrito: int | None
    hex_id: str
