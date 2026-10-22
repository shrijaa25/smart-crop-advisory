from pydantic import BaseModel, ConfigDict, Field


class FarmerRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=10, max_length=30)
    password: str = Field(min_length=8, max_length=128)
    preferred_language: str = Field(default="en", max_length=20)


class FarmerProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    phone: str | None
    preferred_language: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
