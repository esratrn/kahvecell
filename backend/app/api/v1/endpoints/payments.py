from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.core.responses import ApiResponse, ok
from app.schemas.payment import PaymentOut
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get(
    "/me",
    response_model=ApiResponse[list[PaymentOut]],
    summary="Ödeme geçmişim",
    description="Başarısız denemeler de listelenir. En yeni ödeme en üstte.",
)
def my_payments(
    user: CurrentUser,
    db: DbSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    payments = SubscriptionService(db).payment_history(user, offset=offset, limit=limit)
    return ok([PaymentOut.from_model(p) for p in payments])
