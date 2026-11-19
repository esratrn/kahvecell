import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from app.core.money import format_try
from app.models import Payment, PaymentPurpose, PaymentStatus, PlanCode
from app.models.base import utcnow


def _passes_luhn(digits: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(digits)):
        number = int(char)
        if index % 2 == 1:
            number = number * 2 - 9 if number > 4 else number * 2
        total += number
    return total % 10 == 0


class CardIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    card_number: str = Field(repr=False, examples=["4242 4242 4242 4242"])
    holder_name: str = Field(min_length=2, max_length=100, examples=["Test Kullanıcı"])
    expiry_month: int = Field(ge=1, le=12, examples=[12])
    expiry_year: int = Field(ge=2000, le=2100, examples=[2030])
    cvv: str = Field(repr=False, pattern=r"^\d{3}$", examples=["123"])

    @field_validator("card_number")
    @classmethod
    def _normalize_card_number(cls, value: str) -> str:
        digits = re.sub(r"[\s-]", "", value)
        if not digits.isdigit() or len(digits) != 16 or not _passes_luhn(digits):
            raise ValueError("Geçerli bir kart numarası girin.")
        return digits

    @model_validator(mode="after")
    def _reject_expired(self) -> "CardIn":
        now = utcnow()
        if (self.expiry_year, self.expiry_month) < (now.year, now.month):
            raise ValueError("Kartın son kullanma tarihi geçmiş.")
        return self


class PaymentOut(BaseModel):
    transaction_id: str
    status: PaymentStatus
    purpose: PaymentPurpose
    plan_code: PlanCode
    amount_kurus: int
    card_last4: str
    failure_reason: str | None
    created_at: datetime

    @computed_field
    @property
    def amount_display(self) -> str:
        return format_try(self.amount_kurus)

    @classmethod
    def from_model(cls, payment: Payment) -> "PaymentOut":
        return cls(
            transaction_id=payment.transaction_id,
            status=payment.status,
            purpose=payment.purpose,
            plan_code=payment.plan.code,
            amount_kurus=payment.amount_kurus,
            card_last4=payment.card_last4,
            failure_reason=payment.failure_reason,
            created_at=payment.created_at,
        )
