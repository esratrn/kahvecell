import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Payment, PlanCode, Subscription, SubscriptionPlan, SubscriptionStatus


class SubscriptionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_active_plans(self) -> Sequence[SubscriptionPlan]:
        return self.db.scalars(
            select(SubscriptionPlan)
            .where(SubscriptionPlan.is_active.is_(True))
            .order_by(SubscriptionPlan.price_kurus)
        ).all()

    def get_active_plan(self, code: PlanCode) -> SubscriptionPlan | None:
        return self.db.scalar(
            select(SubscriptionPlan).where(
                SubscriptionPlan.code == code, SubscriptionPlan.is_active.is_(True)
            )
        )

    def get_active_for_user(self, user_id: uuid.UUID) -> Subscription | None:
        return self.db.scalar(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )

    def add(self, subscription: Subscription) -> Subscription:
        self.db.add(subscription)
        self.db.flush()
        return subscription


class PaymentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, payment: Payment) -> Payment:
        self.db.add(payment)
        return payment

    def list_for_user(self, user_id: uuid.UUID, *, offset: int, limit: int) -> Sequence[Payment]:
        return self.db.scalars(
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
