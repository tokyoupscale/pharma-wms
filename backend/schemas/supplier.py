from pydantic import BaseModel


class SupplierCreate(BaseModel):
    name: str
    is_manufacturer: bool = False
    contact_person: str | None = None
    phone: str | None = None
    inn: str | None = None
    notes: str | None = None

class SupplierOut(BaseModel):
    id: int
    name: str
    is_manufacturer: bool
    contact_person: str | None
    phone: str | None
    inn: str | None
    is_active: bool
    notes: str | None

    model_config = {"from_attributes": True}