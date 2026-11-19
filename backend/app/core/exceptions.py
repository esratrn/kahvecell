from typing import Any


class AppError(Exception):
    status_code = 400
    code = "BAD_REQUEST"
    message = "İstek işlenemedi."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: Any = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.details = details
        super().__init__(self.message)


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"
    message = "Bu işlem için giriş yapmalısınız."


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"
    message = "Bu işlem için yetkiniz yok."


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"
    message = "Kayıt bulunamadı."


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"
    message = "Kayıt zaten mevcut."
