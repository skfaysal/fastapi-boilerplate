from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    is_active: bool
    role: str
    phone_number: str | None

    model_config = {"from_attributes": True}


class UserVerification(BaseModel):
    password: str
    new_password: str = Field(..., min_length=6)
