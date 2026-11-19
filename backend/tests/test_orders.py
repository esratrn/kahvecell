import uuid
from datetime import time, timedelta

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.money import TURKEY_TZ
from app.models import Product, Shop, Subscription, User, UserRole
from app.models.base import utcnow
from app.services import qr_service
from seed.seed_data import seed_shops
from tests.conftest import auth_header, login
from tests.test_subscriptions import SUCCESS_CARD

ORDERS = "/api/v1/orders"
KIZILAY_SHOP = "Meydan Kahve Kızılay"


def _shop_and_product(shop_name: str = KIZILAY_SHOP, product: str = "Caffè Latte"):
    with SessionLocal() as db:
        shop = db.scalar(select(Shop).where(Shop.name == shop_name))
        item = db.scalar(select(Product).where(Product.shop_id == shop.id, Product.name == product))
        return shop.id, item.id


@pytest.fixture
def world(client):
    with SessionLocal.begin() as db:
        seed_shops(db)

    customer = auth_header(login(client, "05551110001"))
    owner = auth_header(login(client, "05441110001"))
    other_owner = auth_header(login(client, "05441110002"))
    with SessionLocal.begin() as db:
        for phone in ("+905441110001", "+905441110002"):
            db.scalar(select(User).where(User.phone_number == phone)).role = UserRole.SHOP_OWNER
        owner_user = db.scalar(select(User).where(User.phone_number == "+905441110001"))
        db.scalar(select(Shop).where(Shop.name == KIZILAY_SHOP)).owner_id = owner_user.id

    shop_id, product_id = _shop_and_product()
    return {
        "client": client,
        "customer": customer,
        "owner": owner,
        "other_owner": other_owner,
        "shop_id": str(shop_id),
        "product_id": str(product_id),
    }


def subscribe(world, plan="STARTER", headers=None):
    response = world["client"].post(
        "/api/v1/subscriptions",
        headers=headers or world["customer"],
        json={"plan_code": plan, "card": SUCCESS_CARD},
    )
    assert response.status_code == 201, response.text


def order_body(world, **overrides):
    return {
        "shop_id": world["shop_id"],
        "product_id": world["product_id"],
        "size": "L",
        "sugar_level": 1,
        "milk": "OAT",
        "extra_shots": 1,
        **overrides,
    }


def place(world, headers=None, **overrides):
    return world["client"].post(ORDERS, headers=headers or world["customer"], json=order_body(world, **overrides))


def set_status(world, order_id, status, headers=None):
    return world["client"].patch(
        f"{ORDERS}/{order_id}/status", headers=headers or world["owner"], json={"status": status}
    )


def remaining_credits(world):
    return world["client"].get("/api/v1/subscriptions/me", headers=world["customer"]).json()["data"][
        "remaining_credits"
    ]


def test_order_requires_active_subscription(world):
    response = place(world)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NO_ACTIVE_SUBSCRIPTION"


def test_order_deducts_one_credit_and_returns_signed_qr(world):
    subscribe(world)

    response = place(world)

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["remaining_credits"] == 9
    order = data["order"]
    assert order["status"] == "PENDING"
    assert order["credits_used"] == 1
    assert order["item"]["product_name"] == "Caffè Latte"
    assert order["item"]["summary"] == "L boy · Yulaf sütü · Az şekerli · 1 ekstra shot"
    assert set(order["qr"]) == {"order_id", "user_id", "shop_id", "created_at", "signature"}
    assert order["qr"]["order_id"] == order["id"]
    assert order["qr"]["shop_id"] == world["shop_id"]
    assert order["qr"]["created_at"].endswith("Z")
    assert qr_service.is_authentic(order["qr"])
    assert remaining_credits(world) == 9


def test_order_is_rejected_when_credits_run_out(world):
    subscribe(world)
    with SessionLocal.begin() as db:
        db.scalar(select(Subscription)).remaining_credits = 0

    response = place(world)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NO_CREDITS_LEFT"
    assert "yenilenecek" in response.json()["error"]["message"]


def test_unlimited_plan_does_not_consume_credits_and_gets_priority(world):
    subscribe(world, plan="UNLIMITED")

    data = place(world).json()["data"]

    assert data["remaining_credits"] is None
    assert data["order"]["credits_used"] == 0
    assert data["order"]["is_priority"] is True


def test_product_must_belong_to_selected_shop(world):
    subscribe(world)
    _, other_shop_product = _shop_and_product("Tunalı Kahve Kavurma", "Flat White")

    response = place(world, product_id=str(other_shop_product))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PRODUCT_NOT_FOUND"
    assert remaining_credits(world) == 10


def test_closed_shop_rejects_orders_without_consuming_credit(world):
    subscribe(world)
    local_now = utcnow().astimezone(TURKEY_TZ)
    with SessionLocal.begin() as db:
        shop = db.get(Shop, uuid.UUID(world["shop_id"]))
        shop.opening_time = time((local_now.hour + 2) % 24)
        shop.closing_time = time((local_now.hour + 3) % 24)

    response = place(world)
    assert response.json()["error"]["code"] == "SHOP_CLOSED"
    assert remaining_credits(world) == 10


def test_full_lifecycle_with_qr_pickup(world):
    subscribe(world)
    order = place(world).json()["data"]["order"]
    client, order_id, qr = world["client"], order["id"], {"qr": order["qr"]}

    incoming = client.get(f"{ORDERS}/incoming", headers=world["owner"]).json()["data"]
    assert [o["id"] for o in incoming] == [order_id]
    assert incoming[0]["qr"] is None
    assert incoming[0]["next_statuses"] == ["ACCEPTED", "CANCELLED"]

    early = client.post(f"{ORDERS}/qr/redeem", headers=world["owner"], json=qr)
    assert early.json()["error"]["code"] == "ORDER_NOT_READY"

    for status in ("ACCEPTED", "PREPARING", "READY"):
        response = set_status(world, order_id, status)
        assert response.status_code == 200, response.text
        assert response.json()["data"]["status"] == status

    seen_by_customer = client.get(f"{ORDERS}/{order_id}", headers=world["customer"]).json()["data"]
    assert seen_by_customer["status_label"] == "Hazır, teslim alabilirsiniz"
    assert seen_by_customer["ready_at"] is not None

    verified = client.post(f"{ORDERS}/qr/verify", headers=world["owner"], json=qr).json()["data"]
    assert verified["valid"] is True
    assert verified["can_redeem"] is True

    redeemed = client.post(f"{ORDERS}/qr/redeem", headers=world["owner"], json=qr)
    assert redeemed.status_code == 200
    assert redeemed.json()["data"]["status"] == "COMPLETED"
    assert redeemed.json()["data"]["completed_at"] is not None

    again = client.post(f"{ORDERS}/qr/redeem", headers=world["owner"], json=qr)
    assert again.json()["error"]["code"] == "QR_ALREADY_USED"
    assert client.get(f"{ORDERS}/{order_id}", headers=world["customer"]).json()["data"]["qr"] is None


def test_invalid_transitions_are_rejected(world):
    subscribe(world)
    order_id = place(world).json()["data"]["order"]["id"]

    skipped = set_status(world, order_id, "READY")
    assert skipped.status_code == 409
    assert skipped.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"
    assert skipped.json()["error"]["details"]["allowed"] == ["ACCEPTED", "CANCELLED"]

    assert set_status(world, order_id, "COMPLETED").json()["error"]["code"] == "QR_REQUIRED"


@pytest.mark.parametrize(
    "tamper",
    [
        lambda qr: {**qr, "signature": "0" * 64},
        lambda qr: {**qr, "user_id": str(uuid.uuid4())},
        lambda qr: {**qr, "created_at": "2020-01-01T00:00:00Z"},
        lambda qr: {**qr, "order_id": str(uuid.uuid4())},
    ],
)
def test_forged_qr_codes_are_rejected(world, tamper):
    subscribe(world)
    qr = place(world).json()["data"]["order"]["qr"]

    response = world["client"].post(f"{ORDERS}/qr/verify", headers=world["owner"], json={"qr": tamper(qr)})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_QR"


def test_other_shop_owner_cannot_see_or_redeem(world):
    subscribe(world)
    order = place(world).json()["data"]["order"]
    client = world["client"]

    assert client.get(f"{ORDERS}/incoming", headers=world["other_owner"]).json()["data"] == []
    assert set_status(world, order["id"], "ACCEPTED", headers=world["other_owner"]).status_code == 404
    response = client.post(f"{ORDERS}/qr/verify", headers=world["other_owner"], json={"qr": order["qr"]})
    assert response.json()["error"]["code"] == "QR_WRONG_SHOP"


def test_customer_cannot_use_shop_endpoints(world):
    subscribe(world)
    order_id = place(world).json()["data"]["order"]["id"]

    assert set_status(world, order_id, "ACCEPTED", headers=world["customer"]).status_code == 403
    assert world["client"].get(f"{ORDERS}/incoming", headers=world["customer"]).status_code == 403


def test_customer_cancel_refunds_credit_only_while_pending(world):
    subscribe(world)
    first = place(world).json()["data"]["order"]["id"]
    second = place(world).json()["data"]["order"]["id"]
    assert remaining_credits(world) == 8

    cancelled = world["client"].post(f"{ORDERS}/{first}/cancel", headers=world["customer"])
    assert cancelled.json()["data"]["status"] == "CANCELLED"
    assert remaining_credits(world) == 9

    set_status(world, second, "ACCEPTED")
    late = world["client"].post(f"{ORDERS}/{second}/cancel", headers=world["customer"])
    assert late.json()["error"]["code"] == "ORDER_NOT_CANCELLABLE"


def test_shop_rejection_refunds_credit(world):
    subscribe(world)
    order_id = place(world).json()["data"]["order"]["id"]

    assert set_status(world, order_id, "CANCELLED").json()["data"]["cancelled_at"] is not None
    assert remaining_credits(world) == 10


def test_history_and_reorder(world):
    subscribe(world)
    original = place(world, note="Bardağa isim: Esra").json()["data"]["order"]

    reordered = world["client"].post(f"{ORDERS}/{original['id']}/reorder", headers=world["customer"])
    assert reordered.status_code == 201
    copy = reordered.json()["data"]["order"]
    assert copy["id"] != original["id"]
    assert copy["item"] == original["item"]
    assert copy["note"] == "Bardağa isim: Esra"

    history = world["client"].get(f"{ORDERS}/history", headers=world["customer"]).json()["data"]
    assert [o["id"] for o in history] == [copy["id"], original["id"]]


def test_priority_orders_come_first_in_shop_queue(world):
    subscribe(world)
    normal = place(world).json()["data"]["order"]["id"]
    vip = auth_header(login(world["client"], "05551110099"))
    subscribe(world, plan="UNLIMITED", headers=vip)
    priority = place(world, headers=vip).json()["data"]["order"]["id"]

    queue = world["client"].get(f"{ORDERS}/incoming", headers=world["owner"]).json()["data"]
    assert [o["id"] for o in queue] == [priority, normal]


def test_qr_image_is_png(world):
    subscribe(world)
    order_id = place(world).json()["data"]["order"]["id"]

    response = world["client"].get(f"{ORDERS}/{order_id}/qr.png", headers=world["customer"])
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")
    assert world["client"].get(f"{ORDERS}/{order_id}/qr.png", headers=world["owner"]).status_code == 404


def test_expired_subscription_period_blocks_orders(world):
    subscribe(world)
    world["client"].delete("/api/v1/subscriptions/me", headers=world["customer"])
    with SessionLocal.begin() as db:
        sub = db.scalar(select(Subscription))
        sub.started_at = utcnow() - timedelta(days=31)
        sub.expires_at = utcnow() - timedelta(seconds=1)

    assert place(world).json()["error"]["code"] == "NO_ACTIVE_SUBSCRIPTION"
