import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.models import UserRole

_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class UserPreferences(BaseModel):
    coffee_types: list[Annotated[str, Field(min_length=1, max_length=50)]] = Field(
        default_factory=list, max_length=20, examples=[["Caffè Latte", "Türk Kahvesi"]]
    )
    allergens: list[Annotated[str, Field(min_length=1, max_length=50)]] = Field(
        default_factory=list, max_length=20, examples=[["laktoz"]]
    )


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phone_number: str
    full_name: str | None
    email: str | None
    role: UserRole
    preferences: UserPreferences
    is_profile_complete: bool
    created_at: datetime


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str | None = Field(None, min_length=2, max_length=100, examples=["Ayşe Yılmaz"])
    email: Annotated[str, AfterValidator(str.lower)] | None = Field(
        None, max_length=255, pattern=_EMAIL_PATTERN, examples=["ayse@example.com"]
    )
    preferences: UserPreferences | None = None


class RoleUpdate(BaseModel):
    role: UserRole
