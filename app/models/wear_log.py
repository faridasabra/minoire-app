from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base

class WearLog(Base):
    __tablename__ = "wear_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    outfit_id = Column(UUID(as_uuid=True), ForeignKey("outfits.id"), nullable=True)
    clothing_item_id = Column(UUID(as_uuid=True), ForeignKey("clothing_items.id"), nullable=True)
    worn_on = Column(DateTime(timezone=True), nullable=False)
    rating = Column(Integer, nullable=True)
    feedback = Column(String, nullable=True)
    weather_temp = Column(Float, nullable=True)
    weather_condition = Column(String, nullable=True)

    user = relationship("User", back_populates="wear_logs")
    outfit = relationship("Outfit", back_populates="wear_logs")
    clothing_item = relationship("ClothingItem", back_populates="wear_logs")