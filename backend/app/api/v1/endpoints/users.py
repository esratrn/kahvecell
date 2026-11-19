import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.core.responses import ApiResponse, ok
from app.schemas.user import ProfileUpdate, RoleUpdate, UserOut
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=ApiResponse[UserOut], summary="Giriş yapmış kullanıcının profili")
def get_me(user: CurrentUser):
    return ok(UserOut.model_validate(user))


@router.patch(
    "/me",
    response_model=ApiResponse[UserOut],
    summary="Profili tamamla / güncelle",
    description="Gönderilmeyen alanlar değişmez. full_name doldurulunca profil tamamlanmış sayılır.",
)
def update_me(body: ProfileUpdate, user: CurrentUser, db: DbSession):
    return ok(UserOut.model_validate(UserService(db).update_profile(user, body)))


@router.get("", response_model=ApiResponse[list[UserOut]], summary="Kullanıcıları listele (Admin)")
def list_users(
    _admin: AdminUser,
    db: DbSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    users = UserService(db).list_users(offset=offset, limit=limit)
    return ok([UserOut.model_validate(u) for u in users])


@router.patch(
    "/{user_id}/role",
    response_model=ApiResponse[UserOut],
    summary="Kullanıcının rolünü değiştir (Admin)",
)
def change_role(user_id: uuid.UUID, body: RoleUpdate, admin: AdminUser, db: DbSession):
    return ok(UserOut.model_validate(UserService(db).change_role(admin, user_id, body.role)))
