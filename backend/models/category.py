from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    is_active = Column(Boolean, default=True)

    subgroups = relationship("Subgroup", back_populates="category")

class Subgroup(Base):
    __tablename__ = "subgroups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    is_active = Column(Boolean, default=True)

    category = relationship("Category", back_populates="subgroups")
    products = relationship("Product", back_populates="subgroup")