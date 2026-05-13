from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from models.expense import ExpenseType


class ExpenseCreate(BaseModel):
    product_id: int
    department: str
    expense_type: ExpenseType = ExpenseType.requirement
    quantity: Decimal = Field(gt=0)
    purpose: str
    document_number: str | None = None
    expense_date: datetime | None = None
    batch_number: str | None = None
    identification_number: str | None = None
    note: str | None = None


class ExpenseCancelRequest(BaseModel):
    cancel_reason: str


class ExpenseOut(BaseModel):
    id: int
    product_id: int
    product_name: str = ""
    department: str
    expense_type: ExpenseType
    quantity: Decimal
    purpose: str
    document_number: str | None
    expense_date: datetime
    batch_number: str | None
    identification_number: str | None
    note: str | None
    is_cancelled: bool
    cancel_reason: str | None
    cancelled_at: datetime | None
    created_by_id: int
    created_by_name: str = ""
    created_at: datetime
    balance: Decimal | None = None

    model_config = {"from_attributes": True}
