import logging
from collections.abc import Sequence
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.money import format_tr_date, format_try
from app.models import (
    Payment,
    PaymentPurpose,
    PaymentStatus,
    PlanCode,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    User,
)
from app.models.base import utcnow
from app.repositories.subscription_repository import PaymentRepository, SubscriptionRepository
from app.schemas.payment import CardIn
from app.schemas.subscription import PlanChange
from app.services.payment_gateway import ChargeResult, MockPaymentGateway

logger = logging.getLogger(__name__)

BILLING_PERIOD = timedelta(days=30)


class PaymentFailedError(AppError):
    status_code = 402
    code = "PAYMENT_FAILED"

    def __init__(self, result: ChargeResult) -> None:
        super().__init__(
            f"Ödeme başarısız: {result.failure_reason}",
            details={"transaction_id": result.transaction_id, "amount_kurus": result.amount_kurus},
        )


class SubscriptionService:
    def __init__(self, db: Session, gateway: MockPaymentGateway | None = None) -> None:
        self.db = db
        self.subscriptions = SubscriptionRepository(db)
        self.payments = PaymentRepository(db)
        self.gateway = gateway or MockPaymentGateway()

    def list_plans(self) -> Sequence[SubscriptionPlan]:
        return self.subscriptions.list_active_plans()

    def get_current(self, user: User) -> Subscription | None:
        subscription = self.subscriptions.get_active_for_user(user.id)
        if subscription is not None and subscription.expires_at <= utcnow():
            # Zamanlayıcı yerine dönem bitişi ilk erişimde işlenir (yenile ya da sonlandır).
            self._close_period(subscription)
            self.db.commit()
            if subscription.status != SubscriptionStatus.ACTIVE:
                return None
        return subscription

    def subscribe(self, user: User, plan_code: PlanCode, card: CardIn) -> tuple[Subscription, Payment]:
        current = self.get_current(user)
        if current is not None:
            if not current.auto_renew:
                raise ConflictError(
                    "İptal ettiğiniz abonelik "
                    f"{format_tr_date(current.expires_at)} tarihine kadar geçerli; "
                    "bu tarihten sonra yeni paket alabilirsiniz.",
                    code="ACTIVE_SUBSCRIPTION_EXISTS",
                )
            raise ConflictError(
                "Zaten aktif bir aboneliğiniz var. Paket değiştirmek için yükseltme/düşürme kullanın.",
                code="ACTIVE_SUBSCRIPTION_EXISTS",
            )

        plan = self._get_plan(plan_code)
        card_token = self.gateway.tokenize(card)
        result = self.gateway.charge(card_token.token, plan.price_kurus)
        payment = self._record_payment(user, plan, PaymentPurpose.NEW_SUBSCRIPTION, result, card_token.last4)
        if not result.success:
            self.db.commit()
            raise PaymentFailedError(result)

        now = utcnow()
        subscription = self.subscriptions.add(
            Subscription(
                user_id=user.id,
                plan=plan,
                status=SubscriptionStatus.ACTIVE,
                remaining_credits=plan.monthly_credits,
                remaining_guest_passes=plan.guest_passes,
                started_at=now,
                expires_at=now + BILLING_PERIOD,
                payment_method_token=card_token.token,
                card_last4=card_token.last4,
            )
        )
        payment.subscription_id = subscription.id
        self.db.commit()
        logger.info("Subscription %s started on %s (txn %s)", subscription.id, plan.code, result.transaction_id)
        return subscription, payment

    def change_plan(
        self, user: User, plan_code: PlanCode, card: CardIn | None
    ) -> tuple[Subscription, Payment | None, PlanChange, str]:
        subscription = self._require_current(user)
        new_plan = self._get_plan(plan_code)
        current_plan = subscription.plan

        if new_plan.id == current_plan.id:
            if subscription.pending_plan is not None:
                subscription.pending_plan = None
                self.db.commit()
                return subscription, None, PlanChange.DOWNGRADE_CANCELLED, (
                    f"Paket düşürme iptal edildi; {current_plan.name} paketiniz devam edecek."
                )
            raise AppError(f"Zaten {current_plan.name} paketini kullanıyorsunuz.", code="SAME_PLAN")

        if new_plan.price_kurus > current_plan.price_kurus:
            payment = self._upgrade(user, subscription, current_plan, new_plan, card)
            return subscription, payment, PlanChange.UPGRADED, (
                f"{new_plan.name} paketine geçildi. Fark ücreti "
                f"{format_try(payment.amount_kurus)} tahsil edildi."
            )

        if not subscription.auto_renew:
            raise AppError(
                "İptal edilmiş aboneliğin paketi düşürülemez; dönem sonunda sona erecek.",
                code="SUBSCRIPTION_CANCELLED",
            )
        subscription.pending_plan = new_plan
        self.db.commit()
        return subscription, None, PlanChange.DOWNGRADE_SCHEDULED, (
            f"{format_tr_date(subscription.expires_at)} tarihine kadar {current_plan.name} "
            f"paketiniz geçerli; sonraki dönemden itibaren {new_plan.name} paketine geçilecek."
        )

    def cancel(self, user: User) -> tuple[Subscription, str]:
        subscription = self._require_current(user)
        if not subscription.auto_renew:
            raise ConflictError("Abonelik zaten iptal edilmiş.", code="ALREADY_CANCELLED")
        subscription.auto_renew = False
        subscription.cancelled_at = utcnow()
        subscription.pending_plan = None
        self.db.commit()
        return subscription, (
            "Aboneliğiniz iptal edildi. Kalan haklarınızı "
            f"{format_tr_date(subscription.expires_at)} tarihine kadar kullanabilirsiniz."
        )

    def payment_history(self, user: User, *, offset: int, limit: int) -> Sequence[Payment]:
        return self.payments.list_for_user(user.id, offset=offset, limit=limit)

    def _upgrade(
        self,
        user: User,
        subscription: Subscription,
        current_plan: SubscriptionPlan,
        new_plan: SubscriptionPlan,
        card: CardIn | None,
    ) -> Payment:
        if card is not None:
            card_token = self.gateway.tokenize(card)
            token, last4 = card_token.token, card_token.last4
        else:
            token, last4 = subscription.payment_method_token, subscription.card_last4
        if token is None or last4 is None:
            raise AppError(
                "Bu abonelikte kayıtlı kart yok; yükseltme için kart bilgisi gönderin.",
                code="CARD_REQUIRED",
                status_code=422,
            )

        # Dönem ortasında yükseltmede yalnızca iki paket arasındaki fark alınır.
        result = self.gateway.charge(token, new_plan.price_kurus - current_plan.price_kurus)
        payment = self._record_payment(user, new_plan, PaymentPurpose.UPGRADE, result, last4)
        payment.subscription_id = subscription.id
        if not result.success:
            self.db.commit()
            raise PaymentFailedError(result)

        if new_plan.is_unlimited:
            subscription.remaining_credits = None
        else:
            # Kullanılmamış haklar korunur, yeni paketin ek hakları üzerine eklenir.
            subscription.remaining_credits = (
                (subscription.remaining_credits or 0)
                + new_plan.monthly_credits
                - current_plan.monthly_credits
            )
        subscription.remaining_guest_passes += max(0, new_plan.guest_passes - current_plan.guest_passes)
        subscription.plan = new_plan
        subscription.pending_plan = None
        subscription.payment_method_token, subscription.card_last4 = token, last4
        self.db.commit()
        return payment

    def _close_period(self, subscription: Subscription) -> None:
        if not subscription.auto_renew:
            subscription.status = SubscriptionStatus.CANCELLED
            return
        if subscription.payment_method_token is None or subscription.card_last4 is None:
            subscription.status = SubscriptionStatus.EXPIRED
            return

        plan = subscription.pending_plan or subscription.plan
        result = self.gateway.charge(subscription.payment_method_token, plan.price_kurus)
        payment = self._record_payment(
            subscription.user, plan, PaymentPurpose.RENEWAL, result, subscription.card_last4
        )
        payment.subscription_id = subscription.id
        if not result.success:
            subscription.status = SubscriptionStatus.EXPIRED
            logger.info("Subscription %s expired: renewal payment failed", subscription.id)
            return

        now = utcnow()
        subscription.plan = plan
        subscription.pending_plan = None
        subscription.remaining_credits = plan.monthly_credits
        subscription.remaining_guest_passes = plan.guest_passes
        subscription.started_at = now
        subscription.expires_at = now + BILLING_PERIOD
        logger.info("Subscription %s renewed on %s", subscription.id, plan.code)

    def _require_current(self, user: User) -> Subscription:
        subscription = self.get_current(user)
        if subscription is None:
            raise NotFoundError("Aktif bir aboneliğiniz yok.", code="NO_ACTIVE_SUBSCRIPTION")
        return subscription

    def _get_plan(self, code: PlanCode) -> SubscriptionPlan:
        plan = self.subscriptions.get_active_plan(code)
        if plan is None:
            raise NotFoundError("Paket bulunamadı.", code="PLAN_NOT_FOUND")
        return plan

    def _record_payment(
        self,
        user: User,
        plan: SubscriptionPlan,
        purpose: PaymentPurpose,
        result: ChargeResult,
        card_last4: str,
    ) -> Payment:
        return self.payments.add(
            Payment(
                user_id=user.id,
                plan=plan,
                transaction_id=result.transaction_id,
                purpose=purpose,
                status=PaymentStatus.SUCCESS if result.success else PaymentStatus.FAILED,
                amount_kurus=result.amount_kurus,
                card_last4=card_last4,
                failure_reason=result.failure_reason,
                created_at=result.processed_at,
            )
        )
