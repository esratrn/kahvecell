_TR_UPPER = str.maketrans({"İ": "i", "I": "ı"})
_TR_TO_ASCII = str.maketrans("çğıöşüâîû", "cgiosuaiu")


def normalize_tr(text: str) -> str:
    # "ÇAYYOLU", "Çayyolu" ve "cayyolu" aynı sonuca iner; Türkçe büyük/küçük harf kuralları korunur.
    return text.translate(_TR_UPPER).lower().translate(_TR_TO_ASCII)
