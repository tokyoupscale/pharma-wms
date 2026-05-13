from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime, date
from models.supply import SupplyStatus

class SupplyItemCreate(BaseModel):
    product_id: int
    quantity: Decimal = Field(gt=0)
    package_count: int | None = None  # Кол-во мест
    batch_code: str
    identification_number: str | None = None
    manufacture_date: str | None = None
    expiry_date: date | None = None
    notes: str | None = None

class SupplyItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str = ""
    quantity: Decimal
    package_count: int | None
    batch_code: str
    identification_number: str | None
    manufacture_date: str | None
    expiry_date: date | None
    notes: str | None

    model_config = {"from_attributes": True}


class SupplyCreate(BaseModel):
    invoice_number: str
    invoice_date: date
    edo_flag: bool = False
    supplier_id: int
    manufacturer_id: int | None = None
    notes: str | None = None
    items: list[SupplyItemCreate]


class SupplyOut(BaseModel):
    id: int
    invoice_number: str
    invoice_date: date
    edo_flag: bool
    supplier_id: int
    supplier_name: str = ""
    manufacturer_id: int | None
    status: SupplyStatus
    notes: str | None
    created_at: datetime
    confirmed_at: datetime | None = None
    confirmed_by: int | None = None
    confirmed_by_name: str = ""
    items: list[SupplyItemOut] = []

    model_config = {"from_attributes": True}