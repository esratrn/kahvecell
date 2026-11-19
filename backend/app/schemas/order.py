import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models import CupSize, MilkOption, Order, OrderItem, OrderStatus, ProductCategory

STATUS_LABELS = {
    OrderStatus.PENDING: "Onay bekliyor",
    OrderStatus.ACCEPTED: "Kabul edildi",
    OrderStatus.PREPARING: "Hazırlanıyor",
    OrderStatus.READY: "Hazır, teslim alabilirsiniz",
    OrderStatus.COMPLETED: "Teslim edildi",
    OrderStatus.CANCELLED: "İptal edildi",
}

MILK_LABELS = {
    MilkOption.NONE: "Sütsüz",
    MilkOption.WHOLE: "Tam yağlı süt",
    MilkOption.LACTOSE_FREE: "Laktozsuz süt",
    MilkOption.OAT: "Yulaf sütü",
    MilkOption.ALMOND: "Badem sütü",
    MilkOption.SOY: "Soya sütü",
}

SUGAR_LABELS = {0: "Şekersiz", 1: "Az şekerli", 2: "Orta şekerli", 3: "Çok şekerli"}


class OrderCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    shop_id: uuid.UUID
    product_id: uuid.UUID
    size: CupSize = CupSize.M
    sugar_level: int = Field(0, ge=0, le=3, description="0 şekersiz, 3 çok şekerli")
    milk: MilkOption = MilkOption.NONE
    extra_shots: int = Field(0, ge=0, le=3)
    note: str | None = Field(None, max_length=255, examples=["Bardağa isim: Esra"])


class StatusUpdate(BaseModel):
    status: OrderStatus


class QrPayload(BaseModel):
    order_id: uuid.UUID
    user_id: uuid.UUID
    shop_id: uuid.UUID
    created_at: str = Field(max_length=40, examples=["2026-11-19T20:15:00Z"])
    signature: str = Field(pattern=r"^[0-9a-f]{64}$")

    def as_signed_fields(self) -> dict[str, str]:
        return {
            "order_id": str(self.order_id),
            "user_id": str(self.user_id),
            "shop_id": str(self.shop_id),
            "created_at": self.created_at,
            "signature": self.signature,
        }


class QrScanRequest(BaseModel):
    qr: QrPayload


class OrderItemOut(BaseModel):
    product_id: uuid.UUID
    product_name: str
    category: ProductCategory
    size: CupSize
    sugar_level: int
    milk: MilkOption
    extra_shots: int

    @computed_field
    @property
    def summary(self) -> str:
        parts = [f"{self.size.value} boy", MILK_LABELS[self.milk], SUGAR_LABELS[self.sugar_level]]
        if self.extra_shots:
            parts.append(f"{self.extra_shots} ekstra shot")
        return " · ".join(parts)

    @classmethod
    def build(cls, item: OrderItem) -> "OrderItemOut":
        return cls(
            product_id=item.product_id,
            product_name=item.product.name,
            category=item.product.category,
            size=item.size,
            sugar_level=item.sugar_level,
            milk=item.milk,
            extra_shots=item.extra_shots,
        )


class OrderShopOut(BaseModel):
    id: uuid.UUID
    name: str
    address: str


class OrderOut(BaseModel):
    id: uuid.UUID
    status: OrderStatus
    shop: OrderShopOut
    item: OrderItemOut
    customer_name: str | None
    credits_used: int
    is_priority: bool
    note: str | None
    created_at: datetime
    accepted_at: datetime | None
    preparing_at: datetime | None
    ready_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    # Dükkân sahibinin bu siparişi geçirebileceği durumlar.
    next_statuses: list[OrderStatus]
    # Yalnızca siparişin sahibine döner; dükkânda okutulacak içerik (case 13.2).
    qr: dict[str, str] | None = None
    qr_payload: str | None = None

    @computed_field
    @property
    def status_label(self) -> str:
        return STATUS_LABELS[self.status]


class OrderCreated(BaseModel):
    order: OrderOut
    # null = sınırsız paket
    remaining_credits: int | None


class QrVerification(BaseModel):
    valid: bool
    can_redeem: bool
    message: str
    order: OrderOut


def build_order_out(
    order: Order,
    *,
    next_statuses: list[OrderStatus],
    qr: dict[str, str] | None = None,
    qr_payload: str | None = None,
) -> OrderOut:
    return OrderOut(
        id=order.id,
        status=order.status,
        shop=OrderShopOut(id=order.shop.id, name=order.shop.name, address=order.shop.address),
        item=OrderItemOut.build(order.items[0]),
        customer_name=order.user.full_name,
        credits_used=order.credits_used,
        is_priority=order.is_priority,
        note=order.note,
        created_at=order.created_at,
        accepted_at=order.accepted_at,
        preparing_at=order.preparing_at,
        ready_at=order.ready_at,
        completed_at=order.completed_at,
        cancelled_at=order.cancelled_at,
        next_statuses=next_statuses,
        qr=qr,
        qr_payload=qr_payload,
    )
