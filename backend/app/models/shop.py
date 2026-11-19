from __future__ import annotations

import uuid
from datetime import time
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.order import Order, OrderItem
    from app.models.user import User


DEFAULT_TIMEZONE = "Europe/Istanbul"


class ProductCategory(StrEnum):
    # Sıralama menüde gösterim sırasıdır.
    ESPRESSO_BASED = "ESPRESSO_BASED"
    FILTER_COFFEE = "FILTER_COFFEE"
    COLD_DRINK = "COLD_DRINK"
    OTHER = "OTHER"


class Shop(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shops"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_shop_latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_shop_longitude"),
        CheckConstraint("rating BETWEEN 0 AND 5", name="ck_shop_rating"),
        # Yakındaki dükkân sorgusu önce enlem/boylam aralığıyla daraltılır, sonra Haversine uygulanır.
        Index("ix_shops_location", "latitude", "longitude"),
    )

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(50), index=True)
    district: Mapped[str | None] = mapped_column(String(50))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    phone: Mapped[str | None] = mapped_column(String(15))
    # Çalışma saatleri dükkânın yerel saatidir (IANA adı, örn. "Europe/Amsterdam").
    timezone: Mapped[str] = mapped_column(
        String(50), default=DEFAULT_TIMEZONE, server_default=DEFAULT_TIMEZONE
    )
    opening_time: Mapped[time] = mapped_column(Time)
    closing_time: Mapped[time] = mapped_column(Time)
    rating: Mapped[float] = mapped_column(Float, default=0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    image_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    owner: Mapped[User | None] = relationship(back_populates="owned_shops")
    products: Mapped[list[Product]] = relationship(
        back_populates="shop", cascade="all, delete-orphan"
    )
    orders: Mapped[list[Order]] = relationship(back_populates="shop")


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("shop_id", "name", name="uq_product_shop_name"),
        CheckConstraint("price_kurus >= 0", name="ck_product_price_non_negative"),
    )

    shop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[ProductCategory] = mapped_column(
        Enum(ProductCategory, native_enum=False, length=20)
    )
    # Menüde gösterilen liste fiyatı; abonelikle alımda kahve hakkından düşülür.
    price_kurus: Mapped[int] = mapped_column(Integer)
    image_url: Mapped[str | None] = mapped_column(String(500))
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)

    shop: Mapped[Shop] = relationship(back_populates="products")
    order_items: Mapped[list[OrderItem]] = relationship(back_populates="product")
