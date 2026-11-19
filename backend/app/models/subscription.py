from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin, utcnow

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.payment import Payment
    from app.models.user import User


class PlanCode(StrEnum):
    STARTER = "STARTER"
    PREMIUM = "PREMIUM"
    UNLIMITED = "UNLIMITED"


class SubscriptionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    __table_args__ = (
        CheckConstraint("price_kurus >= 0", name="ck_plan_price_non_negative"),
        CheckConstraint(
            "monthly_credits IS NULL OR monthly_credits > 0", name="ck_plan_credits_positive"
        ),
        CheckConstraint("guest_passes >= 0", name="ck_plan_guest_passes_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[PlanCode] = mapped_column(
        Enum(PlanCode, native_enum=False, length=20), unique=True
    )
    name: Mapped[str] = mapped_column(String(50))
    # Para kuruş cinsinden tam sayı tutulur (89,99 TL -> 8999); ondalık yuvarlama hatası olmaz.
    price_kurus: Mapped[int] = mapped_column(Integer)
    # NULL = sınırsız kahve hakkı.
    monthly_credits: Mapped[int | None] = mapped_column(Integer)
    guest_passes: Mapped[int] = mapped_column(Integer, default=0)
    has_priority: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    subscriptions: Mapped[list[Subscription]] = relationship(
        back_populates="plan", foreign_keys="Subscription.plan_id"
    )

    @property
    def is_unlimited(self) -> bool:
        return self.monthly_credits is None


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint(
            "remaining_credits IS NULL OR remaining_credits >= 0",
            name="ck_subscription_credits_non_negative",
        ),
        CheckConstraint(
            "remaining_guest_passes >= 0", name="ck_subscription_guest_passes_non_negative"
        ),
        CheckConstraint("expires_at > started_at", name="ck_subscription_dates"),
        Index("ix_subscriptions_user_status", "user_id", "status"),
        # Bir kullanıcının aynı anda yalnızca bir aktif aboneliği olabilir.
        Index(
            "uq_subscriptions_one_active_per_user",
            "user_id",
            unique=True,
            sqlite_where=text("status = 'ACTIVE'"),
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("subscription_plans.id", ondelete="RESTRICT")
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, native_enum=False, length=20),
        default=SubscriptionStatus.ACTIVE,
    )
    # NULL = sınırsız paket.
    remaining_credits: Mapped[int | None] = mapped_column(Integer)
    remaining_guest_passes: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    # İptal edilen abonelik dönem sonuna kadar kullanılabilir, sonra yenilenmez.
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    # Paket düşürme dönem sonunda uygulanır; o zamana kadar mevcut paket geçerlidir.
    pending_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "subscription_plans.id", ondelete="SET NULL", name="fk_subscriptions_pending_plan_id"
        )
    )
    # Ödeme sağlayıcısının verdiği kart anahtarı; kart numarasının kendisi asla saklanmaz.
    payment_method_token: Mapped[str | None] = mapped_column(String(40))
    card_last4: Mapped[str | None] = mapped_column(String(4))

    user: Mapped[User] = relationship(back_populates="subscriptions")
    plan: Mapped[SubscriptionPlan] = relationship(
        back_populates="subscriptions", foreign_keys=[plan_id]
    )
    pending_plan: Mapped[SubscriptionPlan | None] = relationship(foreign_keys=[pending_plan_id])
    orders: Mapped[list[Order]] = relationship(back_populates="subscription")
    payments: Mapped[list[Payment]] = relationship(back_populates="subscription")
