from pydantic import BaseModel, Field


class TodoRequest(BaseModel):
    title: str = Field(..., min_length=3, examples=["Buy groceries"])
    description: str = Field(..., min_length=3, max_length=100, examples=["Milk, eggs, bread"])
    priority: int = Field(..., gt=0, lt=6, examples=[3])
    complete: bool = Field(default=False, examples=[False])


class TodoResponse(BaseModel):
    id: int
    title: str
    description: str | None
    priority: int
    complete: bool
    owner_id: int

    model_config = {"from_attributes": True}
