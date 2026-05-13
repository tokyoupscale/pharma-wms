from pydantic import BaseModel
from models.product import UnitEnum
from decimal import Decimal


class ProductCreate(BaseModel):
    name: str
    nomenclature_code: str | None = None
    unit: UnitEnum
    category_id: int
    subgroup_id: int | None = None
    min_stock: Decimal = Decimal("0")
    shelf_location: str | None = None
    cell_location: str | None = None
    storage_condition: str | None = None
    notes: str | None = None

class ProductOut(BaseModel):
    id: int
    name: str
    nomenclature_code: str | None
    unit: UnitEnum
    category_id: int
    subgroup_id: int | None
    min_stock: Decimal
    current_stock: Decimal
    shelf_location: str | None
    cell_location: str | None
    storage_condition: str | None
    is_active: bool
    low_stock: bool = False

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_flag(cls, product):
        obj = cls.model_validate(product)
        obj.low_stock = product.current_stock < product.min_stock
        return obj

class ProductUpdate(BaseModel):
    name: str | None = None
    nomenclature_code: str | None = None
    unit: UnitEnum | None = None
    min_stock: Decimal | None = None
    shelf_location: str | None = None
    cell_location: str | None = None
    storage_condition: str | None = None
    notes: str | None = None