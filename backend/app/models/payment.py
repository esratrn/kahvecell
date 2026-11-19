from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import UTCDateTime, UUIDPrimaryKeyMixin, utcnow

if TYPE_CHECKING:
    from app.models.subscription import Subscription, SubscriptionPlan


class PaymentStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class PaymentPurpose(StrEnum):
    NEW_SUBSCRIPTION = "NEW_SUBSCRIPTION"
    UPGRADE = "UPGRADE"
    RENEWAL = "RENEWAL"


class Payment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount_kurus >= 0", name="ck_payment_amount_non_negative"),
        Index("ix_payments_user_created", "user_id", "created_at"),
    )

    # Ödeme kayıtları mali geçmiştir; kullanıcı veya paket silinmek istenirse veritabanı engeller.
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    plan_id: Mapped[int] = mapped_column(ForeignKey("subscription_plans.id", ondelete="RESTRICT"))
    # Başarısız ödemelerde abonelik oluşmadığı için boş kalır.
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="RESTRICT"), index=True
    )
    transaction_id: Mapped[str] = mapped_column(String(40), unique=True)
    purpose: Mapped[PaymentPurpose] = mapped_column(Enum(PaymentPurpose, native_enum=False, length=20))
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus, native_enum=False, length=10))
    amount_kurus: Mapped[int] = mapped_column(Integer)
    card_last4: Mapped[str] = mapped_column(String(4))
    failure_reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    subscription: Mapped[Subscription | None] = relationship(back_populates="payments")
    plan: Mapped[SubscriptionPlan] = relationship()
