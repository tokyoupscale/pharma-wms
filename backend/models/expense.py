from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base


class ExpenseType(str, enum.Enum):
    requirement = "requirement"   # выдача по требованию (цеху)
    sampling    = "sampling"      # отбор пробы ОКК/ООК
    writeoff    = "writeoff"      # списание


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    department = Column(String, nullable=False)   # подразделение-получатель (значение из UserRole)
    expense_type = Column(Enum(ExpenseType), nullable=False, default=ExpenseType.requirement)
    quantity = Column(Numeric(12, 3), nullable=False)
    purpose = Column(String, nullable=False)
    document_number = Column(String, nullable=True)
    expense_date = Column(DateTime, nullable=False, server_default=func.now())
    batch_number = Column(String, nullable=True)
    identification_number = Column(String, nullable=True)  # Идентификационный номер
    note = Column(Text, nullable=True)
    is_cancelled = Column(Boolean, default=False)
    cancel_reason = Column(String, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancelled_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    product = relationship("Product", foreign_keys=[product_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])
