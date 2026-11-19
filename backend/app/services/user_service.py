import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.models import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import ProfileUpdate


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def update_profile(self, user: User, data: ProfileUpdate) -> User:
        changes = data.model_dump(exclude_unset=True)

        if changes.get("full_name") is not None:
            user.full_name = changes["full_name"]
        if "email" in changes:
            email = changes["email"]
            if email is not None:
                owner = self.users.get_by_email(email)
                if owner is not None and owner.id != user.id:
                    raise ConflictError(
                        "Bu e-posta adresi başka bir hesapta kayıtlı.", code="EMAIL_TAKEN"
                    )
            user.email = email
        if changes.get("preferences") is not None:
            user.preferences = changes["preferences"]

        self.db.commit()
        return user

    def list_users(self, *, offset: int, limit: int) -> Sequence[User]:
        return self.users.list(offset=offset, limit=limit)

    def change_role(self, acting_admin: User, user_id: uuid.UUID, role: UserRole) -> User:
        user = self.users.get(user_id)
        if user is None:
            raise NotFoundError("Kullanıcı bulunamadı.")
        if user.id == acting_admin.id and role != UserRole.ADMIN:
            raise AppError(
                "Kendi admin yetkinizi kaldıramazsınız.", code="CANNOT_DEMOTE_SELF"
            )
        user.role = role
        self.db.commit()
        return user
