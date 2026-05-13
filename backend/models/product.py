from sqlalchemy import Column, Integer, String, Boolean, Numeric, ForeignKey, Enum
from sqlalchemy.orm import relationship
from database import Base
import enum


class UnitEnum(str, enum.Enum):
    kg = "kg"
    g = "g"
    l = "l"
    ml = "ml"
    pcs = "pcs" # штук
    pkg = "pkg"
    m = "m"
    roll = "roll"

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True) # Пачка "Аллапинин" табл.
    nomenclature_code = Column(String, nullable=True, index=True)  # УВ-002, ПП-035...
    unit = Column(Enum(UnitEnum), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    subgroup_id = Column(Integer, ForeignKey("subgroups.id"), nullable=True)
    min_stock = Column(Numeric(12, 3), default=0)
    current_stock = Column(Numeric(12, 3), default=0)
    storage_condition = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    shelf_location = Column(String, nullable=True) # стеллаж
    cell_location = Column(String, nullable=True) # ячейка
    manufacturer = Column(String, nullable=True) # производитель (отдельно от поставщика)

    category = relationship("Category")
    subgroup = relationship("Subgroup", back_populates="products")
