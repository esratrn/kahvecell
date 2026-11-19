import logging
import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.core.money import format_tr_date
from app.models import Order, OrderItem, OrderStatus, Product, SubscriptionStatus, User, UserRole
from app.models.base import utcnow
from app.repositories.order_repository import OrderRepository
from app.repositories.shop_repository import ShopRepository
from app.schemas.order import (
    STATUS_LABELS,
    OrderCreate,
    OrderOut,
    QrPayload,
    QrVerification,
    build_order_out,
)
from app.services import qr_service
from app.services.shop_service import is_shop_open
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)

# Dükkânın elle yapabileceği geçişler. Teslim (COMPLETED) yalnızca QR okutularak yapılır.
SHOP_TRANSITIONS: dict[OrderStatus, list[OrderStatus]] = {
    OrderStatus.PENDING: [OrderStatus.ACCEPTED, OrderStatus.CANCELLED],
    OrderStatus.ACCEPTED: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
    OrderStatus.PREPARING: [OrderStatus.READY],
    OrderStatus.READY: [],
    OrderStatus.COMPLETED: [],
    OrderStatus.CANCELLED: [],
}

ACTIVE_STATUSES = [
    OrderStatus.PENDING,
    OrderStatus.ACCEPTED,
    OrderStatus.PREPARING,
    OrderStatus.READY,
]

_TIMESTAMP_FIELDS = {
    OrderStatus.ACCEPTED: "accepted_at",
    OrderStatus.PREPARING: "preparing_at",
    OrderStatus.READY: "ready_at",
    OrderStatus.COMPLETED: "completed_at",
    OrderStatus.CANCELLED: "cancelled_at",
}


class OrderService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.orders = OrderRepository(db)
        self.shops = ShopRepository(db)
        self.subscriptions = SubscriptionService(db)

    def place_order(self, user: User, data: OrderCreate) -> tuple[OrderOut, int | None]:
        shop = self.shops.get_active(data.shop_id)
        if shop is None:
            raise NotFoundError("Dükkân bulunamadı.", code="SHOP_NOT_FOUND")
        product = self.db.get(Product, data.product_id)
        if product is None or product.shop_id != shop.id:
            raise NotFoundError("Bu ürün seçilen dükkânın menüsünde yok.", code="PRODUCT_NOT_FOUND")
        if not product.is_available:
            raise ConflictError(f"{product.name} şu an hazırlanamıyor.", code="PRODUCT_UNAVAILABLE")

        subscription = self.subscriptions.get_current(user)
        if subscription is None:
            raise ForbiddenError(
                "Sipariş verebilmek için aktif bir aboneliğiniz olmalı.",
                code="NO_ACTIVE_SUBSCRIPTION",
            )

        if not is_shop_open(shop, utcnow()):
            raise ConflictError(
                f"{shop.name} şu an kapalı. Çalışma saatleri: "
                f"{shop.opening_time:%H:%M}–{shop.closing_time:%H:%M}.",
                code="SHOP_CLOSED",
            )

        plan = subscription.plan
        credits_used = 0
        if not plan.is_unlimited:
            if not self.orders.consume_credit(subscription.id):
                raise ForbiddenError(
                    "Bu dönemki kahve hakkınız bitti. Hakkınız "
                    f"{format_tr_date(subscription.expires_at)} tarihinde yenilenecek; "
                    "dilerseniz paketinizi yükseltebilirsiniz.",
                    code="NO_CREDITS_LEFT",
                )
            credits_used = 1

        order = Order(
            user_id=user.id,
            shop_id=shop.id,
            subscription_id=subscription.id,
            status=OrderStatus.PENDING,
            credits_used=credits_used,
            is_priority=plan.has_priority,
            note=data.note,
        )
        order.items.append(
            OrderItem(
                product_id=product.id,
                quantity=1,
                size=data.size,
                sugar_level=data.sugar_level,
                milk=data.milk,
                extra_shots=data.extra_shots,
            )
        )
        self.orders.add(order)
        order.qr_signature = qr_service.build_payload(order)["signature"]
        self.db.commit()
        logger.info("Order %s placed at shop %s", order.id, shop.id)

        remaining = None if plan.is_unlimited else subscription.remaining_credits
        return self._to_out(self._load(order.id), as_customer=True), remaining

    def reorder(self, user: User, order_id: uuid.UUID) -> tuple[OrderOut, int | None]:
        previous = self.orders.get(order_id)
        if previous is None or previous.user_id != user.id:
            raise NotFoundError("Sipariş bulunamadı.", code="ORDER_NOT_FOUND")
        item = previous.items[0]
        return self.place_order(
            user,
            OrderCreate(
                shop_id=previous.shop_id,
                product_id=item.product_id,
                size=item.size,
                sugar_level=item.sugar_level,
                milk=item.milk,
                extra_shots=item.extra_shots,
                note=previous.note,
            ),
        )

    def get_for_viewer(self, user: User, order_id: uuid.UUID) -> OrderOut:
        order = self.orders.get(order_id)
        if order is None:
            raise NotFoundError("Sipariş bulunamadı.", code="ORDER_NOT_FOUND")
        is_customer = order.user_id == user.id
        is_staff = self._is_staff_of(user, order)
        if not (is_customer or is_staff):
            # Başkasının siparişinin var olduğu bile belli edilmez.
            raise NotFoundError("Sipariş bulunamadı.", code="ORDER_NOT_FOUND")
        return self._to_out(order, as_customer=is_customer, as_staff=is_staff)

    def qr_png(self, user: User, order_id: uuid.UUID) -> bytes:
        order = self.orders.get(order_id)
        if order is None or order.user_id != user.id:
            raise NotFoundError("Sipariş bulunamadı.", code="ORDER_NOT_FOUND")
        if order.status in (OrderStatus.COMPLETED, OrderStatus.CANCELLED):
            raise ConflictError(
                "Bu siparişin QR kodu artık kullanılamaz.", code="QR_NOT_AVAILABLE"
            )
        return qr_service.render_png(qr_service.build_payload(order))

    def history(self, user: User, *, offset: int, limit: int) -> list[OrderOut]:
        orders = self.orders.list_for_user(user.id, offset=offset, limit=limit)
        return [self._to_out(order, as_customer=True) for order in orders]

    def incoming(
        self,
        staff: User,
        *,
        statuses: Sequence[OrderStatus] | None,
        shop_id: uuid.UUID | None,
        limit: int,
    ) -> list[OrderOut]:
        if staff.role == UserRole.ADMIN:
            shop_ids = [shop_id] if shop_id else [s.id for s in self.shops.list_active()]
        else:
            shop_ids = self.orders.owned_shop_ids(staff.id)
            if shop_id is not None:
                if shop_id not in shop_ids:
                    raise ForbiddenError("Bu dükkânın siparişlerini göremezsiniz.")
                shop_ids = [shop_id]
        if not shop_ids:
            return []
        orders = self.orders.list_for_shops(shop_ids, statuses or ACTIVE_STATUSES, limit=limit)
        return [self._to_out(order, as_staff=True) for order in orders]

    def update_status(self, staff: User, order_id: uuid.UUID, new_status: OrderStatus) -> OrderOut:
        order = self.orders.get(order_id)
        if order is None or not self._is_staff_of(staff, order):
            raise NotFoundError("Sipariş bulunamadı.", code="ORDER_NOT_FOUND")
        if new_status == OrderStatus.COMPLETED:
            raise AppError(
                "Teslim için müşterinin QR kodunu okutun.", code="QR_REQUIRED", status_code=409
            )
        allowed = SHOP_TRANSITIONS[order.status]
        if new_status not in allowed:
            raise ConflictError(
                f"'{STATUS_LABELS[order.status]}' durumundaki sipariş "
                f"'{STATUS_LABELS[new_status]}' durumuna geçirilemez.",
                code="INVALID_STATUS_TRANSITION",
                details={"current": order.status, "allowed": allowed},
            )
        self._transition(order, new_status)
        self.db.commit()
        return self._to_out(order, as_staff=True)

    def cancel_by_customer(self, user: User, order_id: uuid.UUID) -> OrderOut:
        order = self.orders.get(order_id)
        if order is None or order.user_id != user.id:
            raise NotFoundError("Sipariş bulunamadı.", code="ORDER_NOT_FOUND")
        if order.status != OrderStatus.PENDING:
            raise ConflictError(
                "Dükkân siparişi kabul ettiği için artık iptal edilemez.",
                code="ORDER_NOT_CANCELLABLE",
            )
        self._transition(order, OrderStatus.CANCELLED)
        self.db.commit()
        return self._to_out(order, as_customer=True)

    def verify_qr(self, staff: User, qr: QrPayload) -> QrVerification:
        order = self._resolve_qr(staff, qr)
        messages = {
            OrderStatus.READY: "QR kod geçerli. Siparişi teslim edebilirsiniz.",
            OrderStatus.COMPLETED: "QR kod geçerli ancak bu sipariş daha önce teslim edildi.",
            OrderStatus.CANCELLED: "QR kod geçerli ancak sipariş iptal edilmiş.",
        }
        message = messages.get(
            order.status,
            f"QR kod geçerli ancak sipariş henüz hazır değil ({STATUS_LABELS[order.status]}).",
        )
        return QrVerification(
            valid=True,
            can_redeem=order.status == OrderStatus.READY,
            message=message,
            order=self._to_out(order, as_staff=True),
        )

    def redeem_qr(self, staff: User, qr: QrPayload) -> OrderOut:
        order = self._resolve_qr(staff, qr)
        if order.status == OrderStatus.COMPLETED:
            raise ConflictError("Bu QR kod daha önce kullanıldı.", code="QR_ALREADY_USED")
        if order.status == OrderStatus.CANCELLED:
            raise ConflictError("Sipariş iptal edilmiş.", code="ORDER_CANCELLED")
        if order.status != OrderStatus.READY:
            raise ConflictError(
                f"Sipariş henüz hazır değil ({STATUS_LABELS[order.status]}).",
                code="ORDER_NOT_READY",
            )
        self._transition(order, OrderStatus.COMPLETED)
        self.db.commit()
        logger.info("Order %s delivered via QR", order.id)
        return self._to_out(order, as_staff=True)

    def _resolve_qr(self, staff: User, qr: QrPayload) -> Order:
        fields = qr.as_signed_fields()
        invalid = AppError("QR kod geçersiz veya sahte.", code="INVALID_QR")
        if not qr_service.is_authentic(fields):
            logger.warning("Forged QR rejected for order %s", qr.order_id)
            raise invalid
        order = self.orders.get(qr.order_id)
        if order is None or not qr_service.matches_order(fields, order):
            raise invalid
        if not self._is_staff_of(staff, order):
            raise ForbiddenError("Bu sipariş başka bir dükkâna ait.", code="QR_WRONG_SHOP")
        return order

    def _transition(self, order: Order, new_status: OrderStatus) -> None:
        now: datetime = utcnow()
        order.status = new_status
        setattr(order, _TIMESTAMP_FIELDS[new_status], now)
        if new_status == OrderStatus.CANCELLED:
            self._refund_credit(order)

    def _refund_credit(self, order: Order) -> None:
        subscription = order.subscription
        if (
            order.credits_used
            and subscription.status == SubscriptionStatus.ACTIVE
            and subscription.remaining_credits is not None
        ):
            subscription.remaining_credits += order.credits_used

    @staticmethod
    def _is_staff_of(user: User, order: Order) -> bool:
        if user.role == UserRole.ADMIN:
            return True
        return user.role == UserRole.SHOP_OWNER and order.shop.owner_id == user.id

    def _load(self, order_id: uuid.UUID) -> Order:
        order = self.orders.get(order_id)
        assert order is not None
        return order

    def _to_out(self, order: Order, *, as_customer: bool = False, as_staff: bool = False) -> OrderOut:
        qr = None
        if as_customer and order.status not in (OrderStatus.COMPLETED, OrderStatus.CANCELLED):
            qr = qr_service.build_payload(order)
        return build_order_out(
            order,
            next_statuses=SHOP_TRANSITIONS[order.status] if as_staff else [],
            qr=qr,
            qr_payload=qr_service.to_json(qr) if qr else None,
        )
