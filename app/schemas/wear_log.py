from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class WearLogCreate(BaseModel):
    outfit_id: Optional[UUID] = None
    clothing_item_id: Optional[UUID] = None
    worn_on: datetime
    rating: Optional[int] = None
    feedback: Optional[str] = None
    weather_temp: Optional[float] = None
    weather_condition: Optional[str] = None

class WearLogOut(BaseModel):
    id: UUID
    outfit_id: Optional[UUID]
    clothing_item_id: Optional[UUID]
    worn_on: datetime
    rating: Optional[int]
    feedback: Optional[str]
    weather_temp: Optional[float]
    weather_condition: Optional[str]

    model_config = {"from_attributes": True}