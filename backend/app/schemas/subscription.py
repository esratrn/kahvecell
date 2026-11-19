import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, computed_field

from app.core.money import format_try
from app.models import PlanCode, SubscriptionStatus
from app.schemas.payment import CardIn, PaymentOut


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: PlanCode
    name: str
    price_kurus: int
    # null = sınırsız
    monthly_credits: int | None
    is_unlimited: bool
    guest_passes: int
    has_priority: bool

    @computed_field
    @property
    def price_display(self) -> str:
        return format_try(self.price_kurus)

    @computed_field
    @property
    def valid_at(self) -> str:
        return "Tüm dükkânlar"


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: SubscriptionStatus
    plan: PlanOut
    # Dönem sonunda geçilecek (düşürülmüş) paket.
    pending_plan: PlanOut | None
    # null = sınırsız
    remaining_credits: int | None
    remaining_guest_passes: int
    started_at: datetime
    expires_at: datetime
    auto_renew: bool
    cancelled_at: datetime | None
    card_last4: str | None


class SubscribeRequest(BaseModel):
    plan_code: PlanCode
    card: CardIn


class SubscribeResult(BaseModel):
    subscription: SubscriptionOut
    payment: PaymentOut


class PlanChangeRequest(BaseModel):
    plan_code: PlanCode
    # Boş bırakılırsa abonelikte kayıtlı kart kullanılır.
    card: CardIn | None = None


class PlanChange(StrEnum):
    UPGRADED = "UPGRADED"
    DOWNGRADE_SCHEDULED = "DOWNGRADE_SCHEDULED"
    DOWNGRADE_CANCELLED = "DOWNGRADE_CANCELLED"


class PlanChangeResult(BaseModel):
    change: PlanChange
    message: str
    subscription: SubscriptionOut
    payment: PaymentOut | None


class CancelResult(BaseModel):
    message: str
    subscription: SubscriptionOut
