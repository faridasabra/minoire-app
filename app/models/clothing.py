from sqlalchemy import Column, String, Float, DateTime, ForeignKey, ARRAY, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid
from app.database import Base

class ClothingItem(Base):
    __tablename__ = "clothing_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    color = Column(String, nullable=True)
    color_hex = Column(String(7), nullable=True)
    color_secondary = Column(String, nullable=True)
    color_tertiary = Column(String, nullable=True)
    pattern = Column(String, nullable=True)
    formality = Column(String, nullable=True)
    season = Column(ARRAY(String), nullable=True)
    brand = Column(String, nullable=True)
    price = Column(Float, nullable=True)
    image_url = Column(String, nullable=True)
    image_url_clean = Column(String, nullable=True)
    clip_embedding = Column(Vector(512), nullable=True)
    times_worn = Column(Integer, default=0)
    last_worn_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="clothing_items")
    outfit_items = relationship("OutfitItem", back_populates="clothing_item")
    wear_logs = relationship("WearLog", back_populates="clothing_item")