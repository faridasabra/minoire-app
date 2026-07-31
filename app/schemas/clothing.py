from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, List

class ClothingItemCreate(BaseModel):
    name: str
    category: str
    color: Optional[str] = None
    color_hex: Optional[str] = None
    color_secondary: Optional[str] = None
    color_tertiary: Optional[str] = None
    pattern: Optional[str] = None
    formality: Optional[str] = None
    season: Optional[List[str]] = None
    brand: Optional[str] = None
    price: Optional[float] = None

class ClothingItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    color: Optional[str] = None
    color_hex: Optional[str] = None
    color_secondary: Optional[str] = None
    color_tertiary: Optional[str] = None
    pattern: Optional[str] = None
    formality: Optional[str] = None
    season: Optional[List[str]] = None
    brand: Optional[str] = None
    price: Optional[float] = None

class ClothingItemOut(BaseModel):
    id: UUID
    name: str
    category: str
    color: Optional[str]
    color_hex: Optional[str]
    color_secondary: Optional[str] = None
    color_tertiary: Optional[str] = None
    pattern: Optional[str]
    formality: Optional[str]
    season: Optional[List[str]]
    brand: Optional[str]
    price: Optional[float]
    image_url: Optional[str]
    image_url_clean: Optional[str]
    times_worn: int
    last_worn_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}