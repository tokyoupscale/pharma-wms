from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base


class RequestStatus(str, enum.Enum):
    pending = "pending"   # ожидает одобрения ОМТС
    approved = "approved"  # одобрена, расходы созданы
    rejected = "rejected"  # отклонена


class MaterialRequest(Base):
    __tablename__ = "material_requests"

    id = Column(Integer, primary_key=True, index=True)
    department     = Column(String, nullable=False)   # значение из UserRole цеха
    status         = Column(Enum(RequestStatus), nullable=False, default=RequestStatus.pending)
    notes          = Column(Text, nullable=True)
    reject_reason  = Column(String, nullable=True)
    created_by_id  = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at     = Column(DateTime, server_default=func.now())
    approved_at    = Column(DateTime, nullable=True)

    created_by  = relationship("User", foreign_keys=[created_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    items       = relationship("MaterialRequestItem", back_populates="request", cascade="all, delete-orphan")


class MaterialRequestItem(Base):
    __tablename__ = "material_request_items"

    id         = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("material_requests.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity   = Column(Numeric(12, 3), nullable=False)
    notes      = Column(String, nullable=True)

    request = relationship("MaterialRequest", back_populates="items")
    product = relationship("Product", foreign_keys=[product_id])
