from pydantic import BaseModel, EmailStr
from datetime import datetime
from enum import Enum

class TipoServicio(str, Enum):
    especializado = "especializado"
    domicilio_taller = "domicilio_taller"

class AgendamientoBase(BaseModel):
    tipo_servicio: TipoServicio
    nombre: str
    apellido: str
    correo: EmailStr
    telefono: str
    patente: str
    fecha_inicio: datetime
    fecha_termino: datetime

class AgendamientoCreate(AgendamientoBase):
    pass

class AgendamientoOut(AgendamientoBase):
    id: int
    creado_en: datetime

    class Config:
        from_attributes = True
