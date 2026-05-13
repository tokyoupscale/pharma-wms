from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, Date, DateTime, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

class SupplyStatus(str, enum.Enum):
    draft = "draft" # в драфте, можно редактировать
    confirmed = "confirmed" # подтвержденный товар

class Supply(Base):
    __tablename__ = "supplies"
    __table_args__ = (
        UniqueConstraint("invoice_number", name="uq_supply_invoice_number"),
    )

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, nullable=False)
    invoice_date = Column(Date, nullable=False)
    edo_flag = Column(Boolean, default=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    manufacturer_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    status = Column(Enum(SupplyStatus), default=SupplyStatus.draft)
    notes = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    confirmed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)

    supplier = relationship("Supplier", foreign_keys=[supplier_id])
    manufacturer = relationship("Supplier", foreign_keys=[manufacturer_id])
    created_user = relationship("User", foreign_keys=[created_by])
    items = relationship("SupplyItem", back_populates="supply", cascade="all, delete-orphan")

class SupplyItem(Base):
    __tablename__ = "supply_items"

    id = Column(Integer, primary_key=True, index=True)
    supply_id = Column(Integer, ForeignKey("supplies.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Numeric(12, 3), nullable=False)
    package_count = Column(Integer, nullable=True)  # Кол-во мест
    batch_code = Column(String, nullable=False)
    identification_number = Column(String, nullable=True)  # Идентификационный номер
    manufacture_date = Column(String, nullable=True)  # Дата изготовления
    expiry_date = Column(Date, nullable=True)  # Годен до
    notes = Column(String, nullable=True)

    supply = relationship("Supply", back_populates="items")
    product = relationship("Product")