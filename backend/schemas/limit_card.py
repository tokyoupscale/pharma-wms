from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from models.limit_card import LimitCardStatus


class LimitCardAllocationCreate(BaseModel):
    product_id: int
    limit_quantity: Decimal = Field(gt=0)  # утверждённый месячный лимит по товару


class LimitCardAllocationOut(BaseModel):
    id: int
    product_id: int
    product_name: str = ""
    limit_quantity: Decimal

    model_config = {"from_attributes": True}


class LimitCardItemOut(BaseModel):
    id: int
    expense_id: int
    product_id: int
    product_name: str = ""
    quantity: Decimal
    operation_date: datetime
    notes: str | None

    model_config = {"from_attributes": True}


class LimitCardOut(BaseModel):
    id: int
    department: str
    month: int
    year: int
    status: LimitCardStatus
    created_at: datetime
    closed_at: datetime | None
    allocations: list[LimitCardAllocationOut] = []
    items: list[LimitCardItemOut] = []

    model_config = {"from_attributes": True}
