from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    environment: str = "development"

    database_url: str = f"sqlite:///{(BACKEND_DIR / 'kahvecell.db').as_posix()}"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    jwt_secret_key: str = "dev-only-kahvecell-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # QR imzası için JWT'den ayrı anahtar: biri sızarsa diğeri etkilenmez.
    qr_signing_key: str = "dev-only-kahvecell-qr-signing-key-change-in-production"

    # SMS simülasyonu: gerçek SMS gönderilmez, her istekte bu kod geçerlidir.
    otp_code: str = "1234"
    otp_expire_minutes: int = 3
    otp_max_attempts: int = 5

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


settings = Settings()
