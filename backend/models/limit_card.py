from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Numeric, UniqueConstraint, Index, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base


class LimitCardStatus(str, enum.Enum):
    open   = "open"
    closed = "closed"


class LimitCard(Base):
    __tablename__ = "limit_cards"
    # Частичный уникальный индекс: только одна открытая ЛЗК на отдел/месяц/год.
    # Закрытые карты (status='closed') не попадают под ограничение.
    __table_args__ = (
        Index(
            "uq_limit_cards_open_per_dept_month",
            "department", "month", "year",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
    )

    id           = Column(Integer, primary_key=True, index=True)
    department   = Column(String, nullable=False)   # значение из UserRole
    month        = Column(Integer, nullable=False)  # 1–12
    year         = Column(Integer, nullable=False)
    status       = Column(Enum(LimitCardStatus), nullable=False, default=LimitCardStatus.open)
    created_at   = Column(DateTime, server_default=func.now())
    closed_at    = Column(DateTime, nullable=True)
    closed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    closed_by   = relationship("User", foreign_keys=[closed_by_id])
    allocations = relationship("LimitCardAllocation", back_populates="limit_card", cascade="all, delete-orphan")
    items       = relationship("LimitCardItem", back_populates="limit_card", cascade="all, delete-orphan")


class LimitCardAllocation(Base):
    """Утверждённый месячный лимит на каждый товар в ЛЗК (строка «Лимит» в бумажной форме М-8)."""
    __tablename__ = "limit_card_allocations"
    __table_args__ = (
        UniqueConstraint("limit_card_id", "product_id", name="uq_allocation_card_product"),
    )

    id            = Column(Integer, primary_key=True, index=True)
    limit_card_id = Column(Integer, ForeignKey("limit_cards.id"), nullable=False)
    product_id    = Column(Integer, ForeignKey("products.id"), nullable=False)
    limit_quantity = Column(Numeric(12, 3), nullable=False)  # утверждённый лимит

    limit_card = relationship("LimitCard", back_populates="allocations")
    product    = relationship("Product", foreign_keys=[product_id])


class LimitCardItem(Base):
    __tablename__ = "limit_card_items"

    id            = Column(Integer, primary_key=True, index=True)
    limit_card_id = Column(Integer, ForeignKey("limit_cards.id"), nullable=False)
    expense_id    = Column(Integer, ForeignKey("expenses.id"),    nullable=False)
    product_id    = Column(Integer, ForeignKey("products.id"),    nullable=False)
    quantity      = Column(Numeric(12, 3), nullable=False)
    operation_date = Column(DateTime, nullable=False)
    notes         = Column(String, nullable=True)

    limit_card = relationship("LimitCard",  back_populates="items")
    expense    = relationship("Expense",    foreign_keys=[expense_id])
    product    = relationship("Product",    foreign_keys=[product_id])
