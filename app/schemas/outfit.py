from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from app.schemas.clothing import ClothingItemOut

class OutfitItemOut(BaseModel):
    id: UUID
    clothing_item_id: UUID
    slot: Optional[str]
    clothing_item: ClothingItemOut

    model_config = {"from_attributes": True}

class OutfitCreate(BaseModel):
    name: Optional[str] = None
    occasion: Optional[str] = None
    season: Optional[str] = None
    notes: Optional[str] = None
    clothing_item_ids: List[UUID]
    slots: Optional[List[str]] = None

class OutfitOut(BaseModel):
    id: UUID
    name: Optional[str]
    occasion: Optional[str]
    season: Optional[str]
    composite_score: Optional[float]
    notes: Optional[str]
    created_at: datetime
    items: List[OutfitItemOut]

    model_config = {"from_attributes": True}