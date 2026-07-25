from sqlalchemy import Column, String, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.database import Base

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    undertone = Column(String, nullable=True)
    undertone_lab_value = Column(String, nullable=True)
    hairstyle_id = Column(String, nullable=True)
    hair_color_hex = Column(String(7), nullable=True)
    height = Column(Float, nullable=True)
    chest = Column(Float, nullable=True)
    waist = Column(Float, nullable=True)
    hips = Column(Float, nullable=True)
    inseam = Column(Float, nullable=True)

    user = relationship("User")