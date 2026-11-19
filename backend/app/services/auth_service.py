import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError, ForbiddenError, UnauthorizedError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_secret,
    secrets_match,
)
from app.models import OtpCode, RefreshToken, User
from app.models.base import utcnow
from app.repositories.auth_repository import OtpRepository, RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthResult, OtpSent, TokenPair
from app.schemas.user import UserOut

logger = logging.getLogger(__name__)


def _mask_phone(phone_number: str) -> str:
    return f"{phone_number[:6]}*****{phone_number[-2:]}"


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.otps = OtpRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)

    def request_otp(self, phone_number: str) -> OtpSent:
        now = utcnow()
        lifetime = timedelta(minutes=settings.otp_expire_minutes)
        # Yeni kod istenince eskileri geçersiz olur; aynı anda tek geçerli kod bulunur.
        self.otps.consume_all(phone_number, now)
        code = settings.otp_code
        self.otps.add(
            OtpCode(phone_number=phone_number, code_hash=hash_secret(code), expires_at=now + lifetime)
        )
        self.db.commit()
        logger.info("OTP sent (simulated) to %s", _mask_phone(phone_number))
        return OtpSent(
            phone_number=phone_number,
            expires_in_seconds=int(lifetime.total_seconds()),
            dev_otp_code=code if settings.is_development else None,
        )

    def verify_otp(self, phone_number: str, otp_code: str) -> AuthResult:
        now = utcnow()
        otp = self.otps.latest_unconsumed(phone_number)
        if otp is None:
            raise AppError(
                "Bu numara için geçerli bir doğrulama kodu yok. Lütfen yeni kod isteyin.",
                code="OTP_NOT_FOUND",
            )
        if otp.expires_at <= now:
            otp.consumed_at = now
            self.db.commit()
            raise AppError(
                "Doğrulama kodunun süresi doldu. Lütfen yeni kod isteyin.", code="OTP_EXPIRED"
            )
        if not secrets_match(otp_code, otp.code_hash):
            self._register_failed_attempt(otp, now)

        otp.consumed_at = now
        user = self.users.get_by_phone(phone_number)
        is_new_user = user is None
        if user is None:
            user = self.users.add(User(phone_number=phone_number))
            logger.info("New user registered: %s", user.id)
        if not user.is_active:
            self.db.commit()
            raise ForbiddenError("Hesabınız askıya alınmış.", code="ACCOUNT_DISABLED")

        tokens = self._issue_tokens(user)
        self.db.commit()
        return AuthResult(**tokens.model_dump(), is_new_user=is_new_user, user=UserOut.model_validate(user))

    def refresh(self, raw_refresh_token: str) -> TokenPair:
        now = utcnow()
        stored = self.refresh_tokens.get_by_hash(hash_secret(raw_refresh_token))
        if stored is None:
            raise UnauthorizedError("Oturum anahtarı geçersiz.", code="INVALID_REFRESH_TOKEN")
        if stored.revoked_at is not None:
            # Kullanılmış bir anahtarın tekrar gelmesi çalındığına işaret eder: tüm oturumlar kapatılır.
            self.refresh_tokens.revoke_all_for_user(stored.user_id, now)
            self.db.commit()
            logger.warning("Refresh token reuse detected for user %s", stored.user_id)
            raise UnauthorizedError("Oturum anahtarı geçersiz.", code="INVALID_REFRESH_TOKEN")
        if stored.expires_at <= now:
            raise UnauthorizedError(
                "Oturum süresi doldu, lütfen tekrar giriş yapın.", code="REFRESH_TOKEN_EXPIRED"
            )
        user = self.users.get(stored.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("Oturum anahtarı geçersiz.", code="INVALID_REFRESH_TOKEN")

        stored.revoked_at = now
        tokens = self._issue_tokens(user)
        self.db.commit()
        return tokens

    def logout(self, raw_refresh_token: str) -> None:
        stored = self.refresh_tokens.get_by_hash(hash_secret(raw_refresh_token))
        if stored is not None and stored.revoked_at is None:
            stored.revoked_at = utcnow()
            self.db.commit()

    def _register_failed_attempt(self, otp: OtpCode, now: datetime) -> None:
        otp.attempts += 1
        remaining = settings.otp_max_attempts - otp.attempts
        if remaining <= 0:
            otp.consumed_at = now
            self.db.commit()
            raise AppError(
                "Çok fazla hatalı deneme yapıldı. Lütfen yeni kod isteyin.",
                code="OTP_ATTEMPTS_EXCEEDED",
                status_code=429,
            )
        self.db.commit()
        raise AppError(
            "Doğrulama kodu hatalı.",
            code="INVALID_OTP",
            details={"remaining_attempts": remaining},
        )

    def _issue_tokens(self, user: User) -> TokenPair:
        access_token, expires_in = create_access_token(user.id, user.role.value)
        raw_refresh = generate_refresh_token()
        self.refresh_tokens.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_secret(raw_refresh),
                expires_at=utcnow() + timedelta(days=settings.refresh_token_expire_days),
            )
        )
        return TokenPair(access_token=access_token, refresh_token=raw_refresh, expires_in=expires_in)
