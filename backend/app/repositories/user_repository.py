import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_phone(self, phone_number: str) -> User | None:
        return self.db.scalar(select(User).where(User.phone_number == phone_number))

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def list(self, *, offset: int, limit: int) -> Sequence[User]:
        return self.db.scalars(
            select(User).order_by(User.created_at).offset(offset).limit(limit)
        ).all()

    def add(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user
