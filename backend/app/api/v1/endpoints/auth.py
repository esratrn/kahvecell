from fastapi import APIRouter

from app.api.deps import DbSession
from app.core.responses import ApiResponse, MessageOut, ok
from app.schemas.auth import AuthResult, OtpRequest, OtpSent, RefreshRequest, TokenPair, VerifyOtpRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=ApiResponse[OtpSent],
    summary="GSM numarasına doğrulama kodu gönder (kayıt ve giriş)",
    description=(
        "Yeni ve kayıtlı numaralar için aynı adımdır. SMS simülasyondur: kod her zaman 1234."
    ),
)
def register(body: OtpRequest, db: DbSession):
    return ok(AuthService(db).request_otp(body.phone_number))


@router.post(
    "/verify-otp",
    response_model=ApiResponse[AuthResult],
    summary="Kodu doğrula, oturum anahtarlarını al",
    description=(
        "Numara ilk kez doğrulanıyorsa hesap burada açılır (is_new_user=true). "
        "is_profile_complete=false ise profil tamamlama ekranına yönlendirilir."
    ),
)
def verify_otp(body: VerifyOtpRequest, db: DbSession):
    return ok(AuthService(db).verify_otp(body.phone_number, body.otp_code))


@router.post(
    "/refresh",
    response_model=ApiResponse[TokenPair],
    summary="Kod istemeden oturumu yenile",
    description="Eski refresh_token geçersiz olur; yanıttaki yeni çift saklanmalıdır.",
)
def refresh(body: RefreshRequest, db: DbSession):
    return ok(AuthService(db).refresh(body.refresh_token))


@router.post(
    "/logout",
    response_model=ApiResponse[MessageOut],
    summary="Oturumu kapat",
)
def logout(body: RefreshRequest, db: DbSession):
    AuthService(db).logout(body.refresh_token)
    return ok(MessageOut(message="Oturum kapatıldı."))
