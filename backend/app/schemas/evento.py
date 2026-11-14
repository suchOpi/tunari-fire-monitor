from datetime import datetime
from pydantic import BaseModel, ConfigDict


class EventoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    inicio: datetime
    fin: datetime
    latitude: float
    longitude: float
    sensor_principal: str
    sensores_presentes: list[str]
    en_tunari: bool
    distrito: int | None
    subdistrito: str | None
    hex_id: str
    frp_medio: float | None
    frp_max: float | None
    num_detecciones: int
    candidata: bool
    posible_oclusion: bool
