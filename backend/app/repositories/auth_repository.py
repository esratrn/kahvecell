import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import OtpCode, RefreshToken


class OtpRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def latest_unconsumed(self, phone_number: str) -> OtpCode | None:
        return self.db.scalar(
            select(OtpCode)
            .where(OtpCode.phone_number == phone_number, OtpCode.consumed_at.is_(None))
            .order_by(OtpCode.created_at.desc())
            .limit(1)
        )

    def consume_all(self, phone_number: str, now: datetime) -> None:
        self.db.execute(
            update(OtpCode)
            .where(OtpCode.phone_number == phone_number, OtpCode.consumed_at.is_(None))
            .values(consumed_at=now)
        )

    def add(self, otp: OtpCode) -> OtpCode:
        self.db.add(otp)
        return otp


class RefreshTokenRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    def revoke_all_for_user(self, user_id: uuid.UUID, now: datetime) -> None:
        self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    def add(self, token: RefreshToken) -> RefreshToken:
        self.db.add(token)
        return token
