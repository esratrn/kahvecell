from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.core.responses import ApiResponse, ok
from app.schemas.payment import PaymentOut
from app.schemas.subscription import (
    CancelResult,
    PlanChangeRequest,
    PlanChangeResult,
    PlanOut,
    SubscribeRequest,
    SubscribeResult,
    SubscriptionOut,
)
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])

_TEST_CARDS_NOTE = (
    "Test kartları: 4242 4242 4242 4242 her zaman başarılı, "
    "4000 0000 0000 0002 her zaman başarısız. Gerçek kart bilgisi girmeyin."
)


@router.get("/plans", response_model=ApiResponse[list[PlanOut]], summary="Paketleri listele")
def list_plans(db: DbSession):
    return ok([PlanOut.model_validate(plan) for plan in SubscriptionService(db).list_plans()])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[SubscribeResult],
    summary="Abonelik başlat (mobil ödeme simülasyonu)",
    description=_TEST_CARDS_NOTE,
)
def subscribe(body: SubscribeRequest, user: CurrentUser, db: DbSession):
    subscription, payment = SubscriptionService(db).subscribe(user, body.plan_code, body.card)
    return ok(
        SubscribeResult(
            subscription=SubscriptionOut.model_validate(subscription),
            payment=PaymentOut.from_model(payment),
        )
    )


@router.get(
    "/me",
    response_model=ApiResponse[SubscriptionOut | None],
    summary="Aktif aboneliğim",
    description="Aktif abonelik yoksa data null döner.",
)
def get_my_subscription(user: CurrentUser, db: DbSession):
    subscription = SubscriptionService(db).get_current(user)
    return ok(SubscriptionOut.model_validate(subscription) if subscription else None)


@router.patch(
    "/me",
    response_model=ApiResponse[PlanChangeResult],
    summary="Paket yükselt / düşür",
    description=(
        "Yükseltme hemen geçerli olur ve iki paket arasındaki fark tahsil edilir. "
        "Düşürme dönem sonunda uygulanır. card boş bırakılırsa kayıtlı kart kullanılır. "
        + _TEST_CARDS_NOTE
    ),
)
def change_plan(body: PlanChangeRequest, user: CurrentUser, db: DbSession):
    subscription, payment, change, message = SubscriptionService(db).change_plan(
        user, body.plan_code, body.card
    )
    return ok(
        PlanChangeResult(
            change=change,
            message=message,
            subscription=SubscriptionOut.model_validate(subscription),
            payment=PaymentOut.from_model(payment) if payment else None,
        )
    )


@router.delete(
    "/me",
    response_model=ApiResponse[CancelResult],
    summary="Aboneliği iptal et",
    description="Abonelik dönem sonuna kadar kullanılabilir, sonra yenilenmez.",
)
def cancel_subscription(user: CurrentUser, db: DbSession):
    subscription, message = SubscriptionService(db).cancel(user)
    return ok(CancelResult(message=message, subscription=SubscriptionOut.model_validate(subscription)))
