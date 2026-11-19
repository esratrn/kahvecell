from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.shop import Shop
    from app.models.subscription import Subscription


class UserRole(StrEnum):
    CUSTOMER = "CUSTOMER"
    SHOP_OWNER = "SHOP_OWNER"
    ADMIN = "ADMIN"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    phone_number: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    # OTP doğrulamasından sonra profil tamamlama ekranında doldurulur.
    full_name: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=20), default=UserRole.CUSTOMER
    )
    # Örn. {"coffee_types": ["latte"], "allergens": ["lactose"]}
    preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    subscriptions: Mapped[list[Subscription]] = relationship(back_populates="user")
    orders: Mapped[list[Order]] = relationship(back_populates="user")
    owned_shops: Mapped[list[Shop]] = relationship(back_populates="owner")

    @property
    def is_profile_complete(self) -> bool:
        return bool(self.full_name)
