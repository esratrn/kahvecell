from datetime import datetime, timedelta, timezone

# Türkiye 2016'dan beri yaz saati uygulamadan UTC+3 kullanır.
TURKEY_TZ = timezone(timedelta(hours=3), "TRT")


def format_try(amount_kurus: int) -> str:
    lira, kurus = divmod(amount_kurus, 100)
    return f"{lira:,}".replace(",", ".") + f",{kurus:02d} TL"


def format_tr_date(value: datetime) -> str:
    return value.astimezone(TURKEY_TZ).strftime("%d.%m.%Y")
