import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import CurrentUser, DbSession, require_roles
from app.core.responses import ApiResponse, ok
from app.models import OrderStatus, User, UserRole
from app.schemas.order import OrderCreate, OrderCreated, OrderOut, QrScanRequest, QrVerification, StatusUpdate
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])

ShopStaff = Annotated[User, Depends(require_roles(UserRole.SHOP_OWNER, UserRole.ADMIN))]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[OrderCreated],
    summary="Sipariş ver (abonelik hakkından 1 kahve düşer) ve QR al",
    description=(
        "Aktif abonelik ve kalan kahve hakkı gerekir; Unlimited pakette hak düşmez. "
        "Dükkân açık olmalı ve ürün o dükkânın menüsünde bulunmalıdır."
    ),
)
def place_order(body: OrderCreate, user: CurrentUser, db: DbSession):
    order, remaining = OrderService(db).place_order(user, body)
    return ok(OrderCreated(order=order, remaining_credits=remaining))


@router.get("/history", response_model=ApiResponse[list[OrderOut]], summary="Sipariş geçmişim")
def order_history(
    user: CurrentUser,
    db: DbSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return ok(OrderService(db).history(user, offset=offset, limit=limit))


@router.get(
    "/incoming",
    response_model=ApiResponse[list[OrderOut]],
    summary="Dükkânıma gelen siparişler (Dükkân Sahibi)",
    description=(
        "Varsayılan olarak bekleyen, kabul edilen, hazırlanan ve hazır siparişler gelir. "
        "Öncelikli (Unlimited) siparişler üstte, sonra en eski sipariş önce."
    ),
)
def incoming_orders(
    staff: ShopStaff,
    db: DbSession,
    status_filter: Annotated[list[OrderStatus] | None, Query(alias="status")] = None,
    shop_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    return ok(OrderService(db).incoming(staff, statuses=status_filter, shop_id=shop_id, limit=limit))


@router.post(
    "/qr/verify",
    response_model=ApiResponse[QrVerification],
    summary="QR kodu doğrula (Dükkân Sahibi)",
    description="Sahte veya değiştirilmiş QR kodlar INVALID_QR hatası verir. Sipariş durumu değişmez.",
)
def verify_qr(body: QrScanRequest, staff: ShopStaff, db: DbSession):
    return ok(OrderService(db).verify_qr(staff, body.qr))


@router.post(
    "/qr/redeem",
    response_model=ApiResponse[OrderOut],
    summary="QR okutarak teslim et (Dükkân Sahibi)",
    description="Yalnızca 'Hazır' durumundaki sipariş teslim edilebilir. Her QR bir kez kullanılır.",
)
def redeem_qr(body: QrScanRequest, staff: ShopStaff, db: DbSession):
    return ok(OrderService(db).redeem_qr(staff, body.qr))


@router.get(
    "/{order_id}",
    response_model=ApiResponse[OrderOut],
    summary="Sipariş detayı ve QR kodu",
    description="Müşteri kendi siparişini (QR ile), dükkân sahibi kendi dükkânının siparişini görür.",
)
def get_order(order_id: uuid.UUID, user: CurrentUser, db: DbSession):
    return ok(OrderService(db).get_for_viewer(user, order_id))


@router.get(
    "/{order_id}/qr.png",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}, "description": "QR kod görseli"}},
    summary="QR kodu resim olarak al",
)
def get_order_qr_image(order_id: uuid.UUID, user: CurrentUser, db: DbSession):
    return Response(content=OrderService(db).qr_png(user, order_id), media_type="image/png")


@router.patch(
    "/{order_id}/status",
    response_model=ApiResponse[OrderOut],
    summary="Sipariş durumunu güncelle (Dükkân Sahibi)",
    description=(
        "Akış: PENDING → ACCEPTED → PREPARING → READY. Bekleyen veya kabul edilmiş sipariş "
        "CANCELLED yapılabilir (hak iade edilir). Teslim (COMPLETED) için /orders/qr/redeem kullanılır."
    ),
)
def update_status(order_id: uuid.UUID, body: StatusUpdate, staff: ShopStaff, db: DbSession):
    return ok(OrderService(db).update_status(staff, order_id, body.status))


@router.post(
    "/{order_id}/cancel",
    response_model=ApiResponse[OrderOut],
    summary="Siparişimi iptal et",
    description="Dükkân kabul etmeden önce iptal edilebilir; kahve hakkı iade edilir.",
)
def cancel_order(order_id: uuid.UUID, user: CurrentUser, db: DbSession):
    return ok(OrderService(db).cancel_by_customer(user, order_id))


@router.post(
    "/{order_id}/reorder",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[OrderCreated],
    summary="Aynı siparişi tekrar ver",
)
def reorder(order_id: uuid.UUID, user: CurrentUser, db: DbSession):
    order, remaining = OrderService(db).reorder(user, order_id)
    return ok(OrderCreated(order=order, remaining_credits=remaining))
