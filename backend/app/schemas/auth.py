import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from app.schemas.user import UserOut


def normalize_tr_mobile(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 12 and digits.startswith("90"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) != 10 or not digits.startswith("5"):
        raise ValueError("Geçerli bir GSM numarası girin (örn. 0555 555 55 55).")
    return f"+90{digits}"


PhoneNumber = Annotated[
    str,
    Field(max_length=20, examples=["0555 555 55 55"]),
    AfterValidator(normalize_tr_mobile),
]


class OtpRequest(BaseModel):
    phone_number: PhoneNumber


class OtpSent(BaseModel):
    phone_number: str
    expires_in_seconds: int
    # Yalnızca geliştirme ortamında döner; gerçek SMS olmadığı için kodu görebilmek içindir.
    dev_otp_code: str | None = None


class VerifyOtpRequest(BaseModel):
    phone_number: PhoneNumber
    otp_code: str = Field(pattern=r"^\d{4}$", examples=["1234"])


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthResult(TokenPair):
    is_new_user: bool
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=200)
