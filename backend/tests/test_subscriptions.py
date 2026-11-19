from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import Subscription, SubscriptionStatus
from app.models.base import utcnow
from tests.conftest import auth_header, login

PLANS = "/api/v1/subscriptions/plans"
SUBSCRIBE = "/api/v1/subscriptions"
MY_SUB = "/api/v1/subscriptions/me"
MY_PAYMENTS = "/api/v1/payments/me"

SUCCESS_CARD = {
    "card_number": "4242 4242 4242 4242",
    "holder_name": "Test Kullanıcı",
    "expiry_month": 12,
    "expiry_year": 2030,
    "cvv": "123",
}
DECLINED_CARD = {**SUCCESS_CARD, "card_number": "4000-0000-0000-0002"}


@pytest.fixture
def headers(client):
    return auth_header(login(client))


def subscribe(client, headers, plan="STARTER", card=SUCCESS_CARD):
    return client.post(SUBSCRIBE, headers=headers, json={"plan_code": plan, "card": card})


def expire_current_period() -> None:
    with SessionLocal.begin() as db:
        subscription = db.scalar(
            select(Subscription).where(Subscription.status == SubscriptionStatus.ACTIVE)
        )
        subscription.started_at = utcnow() - timedelta(days=31)
        subscription.expires_at = utcnow() - timedelta(seconds=1)


def test_plans_are_public_and_match_case(client):
    response = client.get(PLANS)

    assert response.status_code == 200
    plans = {p["code"]: p for p in response.json()["data"]}
    assert plans["STARTER"]["price_display"] == "89,99 TL"
    assert plans["STARTER"]["monthly_credits"] == 10
    assert plans["PREMIUM"]["price_kurus"] == 14999
    assert plans["PREMIUM"]["guest_passes"] == 2
    assert plans["UNLIMITED"]["is_unlimited"] is True
    assert plans["UNLIMITED"]["monthly_credits"] is None
    assert plans["UNLIMITED"]["has_priority"] is True


def test_subscribing_requires_login(client):
    assert subscribe(client, {}).status_code == 401


def test_successful_payment_activates_subscription(client, headers):
    response = subscribe(client, headers)

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["subscription"]["status"] == "ACTIVE"
    assert data["subscription"]["plan"]["code"] == "STARTER"
    assert data["subscription"]["remaining_credits"] == 10
    assert data["subscription"]["card_last4"] == "4242"
    assert data["payment"]["status"] == "SUCCESS"
    assert data["payment"]["amount_kurus"] == 8999
    assert data["payment"]["transaction_id"].startswith("TXN-")

    me = client.get(MY_SUB, headers=headers).json()["data"]
    assert me["id"] == data["subscription"]["id"]


def test_declined_card_records_failed_payment_without_subscription(client, headers):
    response = subscribe(client, headers, card=DECLINED_CARD)

    assert response.status_code == 402
    error = response.json()["error"]
    assert error["code"] == "PAYMENT_FAILED"
    assert error["details"]["transaction_id"].startswith("TXN-")
    assert client.get(MY_SUB, headers=headers).json()["data"] is None

    history = client.get(MY_PAYMENTS, headers=headers).json()["data"]
    assert [(p["status"], p["card_last4"]) for p in history] == [("FAILED", "0002")]


@pytest.mark.parametrize(
    ("card", "expected_code"),
    [
        ({**SUCCESS_CARD, "card_number": "5555 5555 5555 4444"}, "CARD_NOT_SUPPORTED"),
        ({**SUCCESS_CARD, "card_number": "4242 4242 4242 4241"}, "VALIDATION_ERROR"),
        ({**SUCCESS_CARD, "expiry_year": 2020}, "VALIDATION_ERROR"),
        ({**SUCCESS_CARD, "cvv": "12"}, "VALIDATION_ERROR"),
    ],
)
def test_invalid_cards_are_rejected_before_charging(client, headers, card, expected_code):
    response = subscribe(client, headers, card=card)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == expected_code
    assert client.get(MY_PAYMENTS, headers=headers).json()["data"] == []


def test_cannot_hold_two_active_subscriptions(client, headers):
    subscribe(client, headers)

    response = subscribe(client, headers, plan="PREMIUM")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ACTIVE_SUBSCRIPTION_EXISTS"


def test_upgrade_charges_difference_and_adds_credits(client, headers):
    subscribe(client, headers)

    response = client.patch(MY_SUB, headers=headers, json={"plan_code": "PREMIUM"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["change"] == "UPGRADED"
    assert data["payment"]["amount_kurus"] == 14999 - 8999
    assert data["payment"]["purpose"] == "UPGRADE"
    assert data["subscription"]["plan"]["code"] == "PREMIUM"
    assert data["subscription"]["remaining_credits"] == 20
    assert data["subscription"]["remaining_guest_passes"] == 2


def test_upgrade_to_unlimited_removes_credit_limit(client, headers):
    subscribe(client, headers)

    data = client.patch(MY_SUB, headers=headers, json={"plan_code": "UNLIMITED"}).json()["data"]
    assert data["subscription"]["remaining_credits"] is None
    assert data["subscription"]["plan"]["is_unlimited"] is True


def test_failed_upgrade_payment_keeps_current_plan(client, headers):
    subscribe(client, headers)

    response = client.patch(
        MY_SUB, headers=headers, json={"plan_code": "PREMIUM", "card": DECLINED_CARD}
    )
    assert response.status_code == 402
    assert client.get(MY_SUB, headers=headers).json()["data"]["plan"]["code"] == "STARTER"


def test_downgrade_is_scheduled_and_can_be_undone(client, headers):
    subscribe(client, headers, plan="PREMIUM")

    scheduled = client.patch(MY_SUB, headers=headers, json={"plan_code": "STARTER"}).json()["data"]
    assert scheduled["change"] == "DOWNGRADE_SCHEDULED"
    assert scheduled["payment"] is None
    assert scheduled["subscription"]["plan"]["code"] == "PREMIUM"
    assert scheduled["subscription"]["pending_plan"]["code"] == "STARTER"

    undone = client.patch(MY_SUB, headers=headers, json={"plan_code": "PREMIUM"}).json()["data"]
    assert undone["change"] == "DOWNGRADE_CANCELLED"
    assert undone["subscription"]["pending_plan"] is None


def test_same_plan_is_rejected(client, headers):
    subscribe(client, headers)

    response = client.patch(MY_SUB, headers=headers, json={"plan_code": "STARTER"})
    assert response.json()["error"]["code"] == "SAME_PLAN"


def test_cancel_keeps_access_until_period_end(client, headers):
    subscribe(client, headers)

    response = client.delete(MY_SUB, headers=headers)
    assert response.status_code == 200
    subscription = response.json()["data"]["subscription"]
    assert subscription["status"] == "ACTIVE"
    assert subscription["auto_renew"] is False
    assert subscription["cancelled_at"] is not None

    assert client.delete(MY_SUB, headers=headers).json()["error"]["code"] == "ALREADY_CANCELLED"
    assert subscribe(client, headers).json()["error"]["code"] == "ACTIVE_SUBSCRIPTION_EXISTS"


def test_period_end_renews_with_saved_card_and_applies_downgrade(client, headers):
    subscribe(client, headers, plan="PREMIUM")
    client.patch(MY_SUB, headers=headers, json={"plan_code": "STARTER"})
    expire_current_period()

    renewed = client.get(MY_SUB, headers=headers).json()["data"]
    assert renewed["plan"]["code"] == "STARTER"
    assert renewed["pending_plan"] is None
    assert renewed["remaining_credits"] == 10

    history = client.get(MY_PAYMENTS, headers=headers).json()["data"]
    assert history[0]["purpose"] == "RENEWAL"
    assert history[0]["amount_kurus"] == 8999


def test_period_end_after_cancel_ends_subscription(client, headers):
    subscribe(client, headers)
    client.delete(MY_SUB, headers=headers)
    expire_current_period()

    assert client.get(MY_SUB, headers=headers).json()["data"] is None
    assert subscribe(client, headers, plan="PREMIUM").status_code == 201


def test_change_and_cancel_require_active_subscription(client, headers):
    patch = client.patch(MY_SUB, headers=headers, json={"plan_code": "PREMIUM"})
    assert patch.status_code == 404
    assert patch.json()["error"]["code"] == "NO_ACTIVE_SUBSCRIPTION"
    assert client.delete(MY_SUB, headers=headers).status_code == 404
