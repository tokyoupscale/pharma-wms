from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from models.request import RequestStatus


class MaterialRequestItemCreate(BaseModel):
    product_id: int
    quantity: Decimal = Field(gt=0)
    notes: str | None = None


class MaterialRequestCreate(BaseModel):
    notes: str | None = None
    items: list[MaterialRequestItemCreate]


class MaterialRequestRejectRequest(BaseModel):
    reject_reason: str


class MaterialRequestItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str = ""
    quantity: Decimal
    notes: str | None

    model_config = {"from_attributes": True}


class MaterialRequestOut(BaseModel):
    id: int
    department: str
    status: RequestStatus
    notes: str | None
    reject_reason: str | None
    created_by_id: int
    created_by_name: str = ""
    approved_by_id: int | None
    approved_by_name: str = ""
    created_at: datetime
    approved_at: datetime | None
    items: list[MaterialRequestItemOut] = []

    model_config = {"from_attributes": True}
