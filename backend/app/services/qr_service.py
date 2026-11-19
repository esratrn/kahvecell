import hashlib
import hmac
import io
import json
from datetime import datetime, timezone

import segno

from app.core.config import settings
from app.models import Order


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sign(order_id: str, user_id: str, shop_id: str, created_at: str) -> str:
    # Alanlar sabit sırayla birleştirilir; JSON anahtar sırası imzayı etkilemez.
    message = "|".join([order_id, user_id, shop_id, created_at]).encode()
    return hmac.new(settings.qr_signing_key.encode(), message, hashlib.sha256).hexdigest()


def build_payload(order: Order) -> dict[str, str]:
    fields = {
        "order_id": str(order.id),
        "user_id": str(order.user_id),
        "shop_id": str(order.shop_id),
        "created_at": _iso_utc(order.created_at),
    }
    return {**fields, "signature": sign(**fields)}


def is_authentic(payload: dict[str, str]) -> bool:
    expected = sign(payload["order_id"], payload["user_id"], payload["shop_id"], payload["created_at"])
    return hmac.compare_digest(expected, payload["signature"])


def matches_order(payload: dict[str, str], order: Order) -> bool:
    return hmac.compare_digest(build_payload(order)["signature"], payload["signature"])


def to_json(payload: dict[str, str]) -> str:
    return json.dumps(payload, separators=(",", ":"))


def render_png(payload: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    segno.make(to_json(payload), error="m").save(buffer, kind="png", scale=8, border=3)
    return buffer.getvalue()
