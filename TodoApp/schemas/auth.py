from pydantic import BaseModel, EmailStr, Field


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, examples=["johndoe"])
    email: EmailStr = Field(..., examples=["john@example.com"])
    first_name: str = Field(..., min_length=1, examples=["John"])
    last_name: str = Field(..., min_length=1, examples=["Doe"])
    password: str = Field(..., min_length=8, examples=["securePass123"])
    role: str = Field(default="user", examples=["user"])
    phone_number: str = Field(default="", examples=["+1-555-555-5555"])


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
