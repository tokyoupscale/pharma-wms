from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str

class CategoryOut(BaseModel):
    id: int
    name: str
    is_active: bool
    model_config = {"from_attributes": True}

class SubgroupCreate(BaseModel):
    name: str
    category_id: int

class SubgroupOut(BaseModel):
    id: int
    name: str
    category_id: int
    is_active: bool
    
    model_config = {"from_attributes": True}