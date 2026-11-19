from datetime import timedelta

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import OtpCode, User, UserRole
from app.models.base import utcnow
from tests.conftest import auth_header, login

REGISTER = "/api/v1/auth/register"
VERIFY = "/api/v1/auth/verify-otp"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/users/me"


def test_register_normalizes_phone_and_returns_dev_code(client):
    response = client.post(REGISTER, json={"phone_number": "0555 111 22 33"})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["data"]["phone_number"] == "+905551112233"
    assert body["data"]["dev_otp_code"] == "1234"


def test_register_rejects_invalid_phone_with_standard_error(client):
    response = client.post(REGISTER, json={"phone_number": "0312 555 01 01"})

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"][0]["field"] == "phone_number"


def test_first_verification_creates_customer_with_incomplete_profile(client):
    tokens = login(client)

    assert tokens["is_new_user"] is True
    assert tokens["user"]["role"] == "CUSTOMER"
    assert tokens["user"]["is_profile_complete"] is False
    assert tokens["access_token"] and tokens["refresh_token"]


def test_second_login_returns_existing_user(client):
    first = login(client)
    second = login(client)

    assert second["is_new_user"] is False
    assert second["user"]["id"] == first["user"]["id"]


def test_verify_without_requesting_code_fails(client):
    response = client.post(VERIFY, json={"phone_number": "05551112233", "otp_code": "1234"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "OTP_NOT_FOUND"


def test_wrong_code_is_limited_and_then_locks(client):
    phone = "05551112233"
    client.post(REGISTER, json={"phone_number": phone})

    for remaining in (4, 3, 2, 1):
        response = client.post(VERIFY, json={"phone_number": phone, "otp_code": "0000"})
        assert response.json()["error"]["code"] == "INVALID_OTP"
        assert response.json()["error"]["details"]["remaining_attempts"] == remaining

    response = client.post(VERIFY, json={"phone_number": phone, "otp_code": "0000"})
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "OTP_ATTEMPTS_EXCEEDED"

    response = client.post(VERIFY, json={"phone_number": phone, "otp_code": "1234"})
    assert response.json()["error"]["code"] == "OTP_NOT_FOUND"


def test_expired_code_is_rejected(client):
    phone = "05551112233"
    client.post(REGISTER, json={"phone_number": phone})
    with SessionLocal.begin() as db:
        otp = db.scalar(select(OtpCode).where(OtpCode.phone_number == "+905551112233"))
        otp.expires_at = utcnow() - timedelta(seconds=1)

    response = client.post(VERIFY, json={"phone_number": phone, "otp_code": "1234"})
    assert response.json()["error"]["code"] == "OTP_EXPIRED"


def test_code_cannot_be_reused(client):
    phone = "05551112233"
    login(client, phone)

    response = client.post(VERIFY, json={"phone_number": phone, "otp_code": "1234"})
    assert response.json()["error"]["code"] == "OTP_NOT_FOUND"


def test_me_requires_token(client):
    assert client.get(ME).json()["error"]["code"] == "UNAUTHORIZED"
    bad = client.get(ME, headers={"Authorization": "Bearer not-a-jwt"})
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "INVALID_TOKEN"


def test_profile_completion(client):
    tokens = login(client)
    response = client.patch(
        ME,
        headers=auth_header(tokens),
        json={
            "full_name": "  Ayşe Yılmaz ",
            "email": "Ayse@Example.com",
            "preferences": {"coffee_types": ["Flat White"], "allergens": ["laktoz"]},
        },
    )

    assert response.status_code == 200
    user = response.json()["data"]
    assert user["full_name"] == "Ayşe Yılmaz"
    assert user["email"] == "ayse@example.com"
    assert user["preferences"]["allergens"] == ["laktoz"]
    assert user["is_profile_complete"] is True
    assert client.get(ME, headers=auth_header(tokens)).json()["data"]["is_profile_complete"]


def test_email_must_be_unique(client):
    first = login(client, "05551112233")
    second = login(client, "05551112244")
    client.patch(ME, headers=auth_header(first), json={"email": "ortak@example.com"})

    response = client.patch(ME, headers=auth_header(second), json={"email": "ortak@example.com"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_TAKEN"


def test_refresh_rotates_tokens_and_detects_reuse(client):
    tokens = login(client)

    rotated = client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]})
    assert rotated.status_code == 200
    new_tokens = rotated.json()["data"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]
    assert client.get(ME, headers=auth_header(new_tokens)).status_code == 200

    reused = client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401
    # Eski anahtarın tekrar kullanılması tüm oturumları kapatır.
    after_reuse = client.post(REFRESH, json={"refresh_token": new_tokens["refresh_token"]})
    assert after_reuse.status_code == 401


def test_logout_revokes_refresh_token(client):
    tokens = login(client)

    assert client.post(LOGOUT, json={"refresh_token": tokens["refresh_token"]}).status_code == 200
    response = client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 401


def _make_admin(phone: str) -> None:
    with SessionLocal.begin() as db:
        db.scalar(select(User).where(User.phone_number == phone)).role = UserRole.ADMIN


def test_only_admin_can_list_users_and_change_roles(client):
    customer = login(client, "05551112233")
    admin = login(client, "05000000000")
    _make_admin("+905000000000")

    assert client.get("/api/v1/users", headers=auth_header(customer)).status_code == 403
    listed = client.get("/api/v1/users", headers=auth_header(admin))
    assert listed.status_code == 200
    assert len(listed.json()["data"]) == 2

    response = client.patch(
        f"/api/v1/users/{customer['user']['id']}/role",
        headers=auth_header(admin),
        json={"role": "SHOP_OWNER"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["role"] == "SHOP_OWNER"
    # Rol token'dan değil veritabanından okunduğu için eski token da yeni rolü görür.
    assert client.get(ME, headers=auth_header(customer)).json()["data"]["role"] == "SHOP_OWNER"


def test_admin_cannot_demote_self(client):
    admin = login(client, "05000000000")
    _make_admin("+905000000000")

    response = client.patch(
        f"/api/v1/users/{admin['user']['id']}/role",
        headers=auth_header(admin),
        json={"role": "CUSTOMER"},
    )
    assert response.json()["error"]["code"] == "CANNOT_DEMOTE_SELF"
