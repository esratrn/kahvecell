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
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.shop import Product, Shop
    from app.models.subscription import Subscription
    from app.models.user import User


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    PREPARING = "PREPARING"
    READY = "READY"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class CupSize(StrEnum):
    S = "S"
    M = "M"
    L = "L"


class MilkOption(StrEnum):
    NONE = "NONE"
    WHOLE = "WHOLE"
    LACTOSE_FREE = "LACTOSE_FREE"
    OAT = "OAT"
    ALMOND = "ALMOND"
    SOY = "SOY"


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("credits_used >= 0", name="ck_order_credits_non_negative"),
        Index("ix_orders_user_created", "user_id", "created_at"),
        Index("ix_orders_shop_status", "shop_id", "status"),
    )

    # Sipariş geçmişi korunmalı: ilişkili kayıt silinmek istenirse veritabanı engeller.
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id", ondelete="RESTRICT"))
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False, length=20), default=OrderStatus.PENDING
    )
    credits_used: Mapped[int] = mapped_column(Integer, default=0)
    # Sipariş anındaki paketin öncelik hakkı (Unlimited); dükkân kuyruğunda üste çıkar.
    is_priority: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    note: Mapped[str | None] = mapped_column(String(255))
    # QR içeriğinin HMAC-SHA256 imzası; teslimde backend bununla doğrular.
    qr_signature: Mapped[str | None] = mapped_column(String(128))
    accepted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    preparing_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    ready_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    user: Mapped[User] = relationship(back_populates="orders")
    shop: Mapped[Shop] = relationship(back_populates="orders")
    subscription: Mapped[Subscription] = relationship(back_populates="orders")
    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_item_quantity_positive"),
        CheckConstraint("sugar_level BETWEEN 0 AND 3", name="ck_order_item_sugar_level"),
        CheckConstraint("extra_shots BETWEEN 0 AND 3", name="ck_order_item_extra_shots"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    size: Mapped[CupSize] = mapped_column(
        Enum(CupSize, native_enum=False, length=2), default=CupSize.M
    )
    # 0 = şekersiz, 3 = çok şekerli
    sugar_level: Mapped[int] = mapped_column(Integer, default=0)
    milk: Mapped[MilkOption] = mapped_column(
        Enum(MilkOption, native_enum=False, length=20), default=MilkOption.NONE
    )
    extra_shots: Mapped[int] = mapped_column(Integer, default=0)

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product] = relationship(back_populates="order_items")
