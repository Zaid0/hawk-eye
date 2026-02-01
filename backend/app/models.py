# app/models.py
from pydantic import BaseModel
from typing import Optional


class TelemetryIn(BaseModel):
    time: float
    lat: float
    lng: float
    alt: Optional[float] = None
    speed: Optional[float] = None
    battery: Optional[float] = None
    gps: Optional[str] = None
    label: Optional[str] = None
    image_base64: Optional[str] = None


class AIResult(BaseModel):
    detected_objects: list
