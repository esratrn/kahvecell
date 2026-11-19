import uuid
from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.models import User, UserRole

DbSession = Annotated[Session, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False, description="verify-otp yanıtındaki access_token")


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise UnauthorizedError()
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError(
            "Oturum süresi doldu, anahtarı yenileyin.", code="TOKEN_EXPIRED"
        ) from None
    except (jwt.InvalidTokenError, ValueError):
        raise UnauthorizedError("Geçersiz oturum anahtarı.", code="INVALID_TOKEN") from None

    # Rol token'dan değil veritabanından okunur: yetki değişikliği anında geçerli olur.
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Geçersiz oturum anahtarı.", code="INVALID_TOKEN")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ForbiddenError()
        return user

    return checker


AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
