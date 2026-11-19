import uuid
from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.models import Order, OrderItem, OrderStatus, Shop, Subscription

_ORDER_RELATIONS = (
    selectinload(Order.shop),
    selectinload(Order.user),
    selectinload(Order.items).selectinload(OrderItem.product),
)


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, order: Order) -> Order:
        self.db.add(order)
        self.db.flush()
        return order

    def get(self, order_id: uuid.UUID) -> Order | None:
        return self.db.scalar(select(Order).where(Order.id == order_id).options(*_ORDER_RELATIONS))

    def list_for_user(self, user_id: uuid.UUID, *, offset: int, limit: int) -> Sequence[Order]:
        return self.db.scalars(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(limit)
            .options(*_ORDER_RELATIONS)
        ).all()

    def list_for_shops(
        self, shop_ids: Sequence[uuid.UUID], statuses: Sequence[OrderStatus], *, limit: int
    ) -> Sequence[Order]:
        return self.db.scalars(
            select(Order)
            .where(Order.shop_id.in_(shop_ids), Order.status.in_(statuses))
            .order_by(Order.is_priority.desc(), Order.created_at)
            .limit(limit)
            .options(*_ORDER_RELATIONS)
        ).all()

    def owned_shop_ids(self, owner_id: uuid.UUID) -> list[uuid.UUID]:
        return list(self.db.scalars(select(Shop.id).where(Shop.owner_id == owner_id)))

    def consume_credit(self, subscription_id: uuid.UUID) -> bool:
        # Koşullu güncelleme: aynı anda gelen iki sipariş son hakkı ikisi birden harcayamaz.
        result = self.db.execute(
            update(Subscription)
            .where(Subscription.id == subscription_id, Subscription.remaining_credits > 0)
            .values(remaining_credits=Subscription.remaining_credits - 1)
            .execution_options(synchronize_session="fetch")
        )
        return result.rowcount == 1
