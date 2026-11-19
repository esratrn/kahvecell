import secrets
from dataclasses import dataclass
from datetime import datetime

from app.core.exceptions import AppError
from app.models.base import utcnow
from app.schemas.payment import CardIn

SUCCESS_TOKEN = "tok_test_success"
DECLINED_TOKEN = "tok_test_declined"

# Case dokümanı 12.1: 4242... her zaman başarılı, 4000...0002 her zaman başarısız.
_TEST_CARDS = {
    "4242424242424242": SUCCESS_TOKEN,
    "4000000000000002": DECLINED_TOKEN,
}


@dataclass(frozen=True)
class CardToken:
    token: str
    last4: str


@dataclass(frozen=True)
class ChargeResult:
    success: bool
    transaction_id: str
    amount_kurus: int
    processed_at: datetime
    failure_reason: str | None


class MockPaymentGateway:
    """Gerçek ödeme sağlayıcısının yerine geçen simülasyon; dışarıya hiçbir istek atmaz."""

    def tokenize(self, card: CardIn) -> CardToken:
        token = _TEST_CARDS.get(card.card_number)
        if token is None:
            raise AppError(
                "Simülasyonda yalnızca test kartları kabul edilir: 4242 4242 4242 4242 "
                "(başarılı) veya 4000 0000 0000 0002 (başarısız). Gerçek kart bilgisi girmeyin.",
                code="CARD_NOT_SUPPORTED",
                status_code=422,
            )
        return CardToken(token=token, last4=card.card_number[-4:])

    def charge(self, token: str, amount_kurus: int) -> ChargeResult:
        now = utcnow()
        success = token == SUCCESS_TOKEN
        return ChargeResult(
            success=success,
            transaction_id=f"TXN-{now:%Y%m%d}-{secrets.token_hex(5).upper()}",
            amount_kurus=amount_kurus,
            processed_at=now,
            failure_reason=None if success else "Kart sağlayıcısı işlemi reddetti.",
        )
