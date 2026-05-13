from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
import enum
from database import Base

class UserRole(str, enum.Enum):
    admin = "admin"
    omts = "omts"
    workshop_afs = "workshop_afs"
    workshop_gls = "workshop_gls"
    quality = "quality"
    quality_assurance = "quality_assurance"
    planning = "planning"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    department = Column(String)
    role = Column(Enum(UserRole), nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    token_version = Column(Integer, default=0, nullable=False, server_default="0")
    created_at = Column(DateTime, server_default=func.now())