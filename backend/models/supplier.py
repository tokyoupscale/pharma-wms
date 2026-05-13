from sqlalchemy import Column, Integer, String, Boolean
from database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    is_manufacturer = Column(Boolean, default=False) # True если это производитель
    contact_person = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    inn = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
