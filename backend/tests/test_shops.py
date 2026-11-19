import uuid
from datetime import datetime, time, timezone

import pytest

from app.core.database import SessionLocal
from app.schemas.shop import ShopListQuery
from app.services.geo import format_distance, haversine_km, is_open_at
from app.services.shop_service import ShopService
from seed.seed_data import seed_shops

SHOPS = "/api/v1/shops"
KIZILAY = {"lat": 39.9208, "lng": 32.8541}


@pytest.fixture
def shops(client):
    with SessionLocal.begin() as db:
        seed_shops(db)
    return client


def names(response) -> list[str]:
    return [shop["name"] for shop in response.json()["data"]]


def test_haversine_matches_known_distance():
    # Aynı boylamda 1 derecelik enlem farkı ~111,19 km'dir.
    assert haversine_km(39.0, 32.85, 40.0, 32.85) == pytest.approx(111.19, abs=0.01)
    assert haversine_km(39.92, 32.85, 39.92, 32.85) == 0


@pytest.mark.parametrize(
    ("opening", "closing", "at", "expected"),
    [
        (time(8), time(22), time(7, 59), False),
        (time(8), time(22), time(8), True),
        (time(8), time(22), time(22), False),
        (time(18), time(2), time(23), True),
        (time(18), time(2), time(1, 59), True),
        (time(18), time(2), time(12), False),
    ],
)
def test_opening_hours_including_overnight(opening, closing, at, expected):
    assert is_open_at(opening, closing, at) is expected


def test_distance_formatting():
    assert format_distance(0.234) == "230 m"
    assert format_distance(2.46) == "2,5 km"
    assert format_distance(2534.3) == "2.534 km"


def test_list_without_location_sorts_by_rating(shops):
    response = shops.get(SHOPS)

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 7
    assert all(shop["distance_km"] is None for shop in data)
    ratings = [shop["rating"] for shop in data]
    assert ratings == sorted(ratings, reverse=True)


def test_nearby_shops_are_sorted_by_distance(shops):
    data = shops.get(SHOPS, params=KIZILAY).json()["data"]

    assert data[0]["name"] == "Meydan Kahve Kızılay"
    assert [shop["name"] for shop in data[-3:]] == [
        "Çayyolu Bahçe Kafe",
        "Konya Kahve Konağı",
        "Maas Koffiebar",
    ]
    assert data[-1]["city"] == "Rotterdam"
    distances = [shop["distance_km"] for shop in data]
    assert distances == sorted(distances)
    assert data[0]["distance_display"].endswith(" m")


def test_radius_limits_results(shops):
    data = shops.get(SHOPS, params={**KIZILAY, "radius": 5}).json()["data"]

    assert "Çayyolu Bahçe Kafe" not in [shop["name"] for shop in data]
    assert all(shop["distance_km"] <= 5 for shop in data)


@pytest.mark.parametrize("q", ["çayyolu", "CAYYOLU", "Çayyolu", "kışlalı"])
def test_search_ignores_turkish_case_and_diacritics(shops, q):
    assert names(shops.get(SHOPS, params={"q": q})) == ["Çayyolu Bahçe Kafe"]


def test_search_matches_address_only_terms(shops):
    # "Sakarya" dükkânın adında değil, yalnızca adresinde geçiyor.
    assert names(shops.get(SHOPS, params={"q": "sakarya"})) == ["Meydan Kahve Kızılay"]


def test_search_combines_with_distance_sorting(shops):
    data = shops.get(SHOPS, params={**KIZILAY, "q": "kahve"}).json()["data"]
    assert [shop["name"] for shop in data] == [
        "Meydan Kahve Kızılay",
        "Tunalı Kahve Kavurma",
        "Yedinci Cadde Kahvecisi",
        "Konya Kahve Konağı",
    ]


def test_search_by_city(shops):
    assert names(shops.get(SHOPS, params={"q": "rotterdam"})) == ["Maas Koffiebar"]
    assert names(shops.get(SHOPS, params={"q": "konya"})) == ["Konya Kahve Konağı"]


def test_min_rating_filter(shops):
    data = shops.get(SHOPS, params={"min_rating": 4.6}).json()["data"]
    assert {shop["name"] for shop in data} == {"Tunalı Kahve Kavurma", "Arjantin Espresso Bar"}


def test_open_now_uses_turkey_local_time(shops):
    # 07:45 Türkiye saati = 04:45 UTC: 7/24 açık Kızılay ve 07:00'de açılan Konya açık.
    early = datetime(2026, 11, 20, 4, 45, tzinfo=timezone.utc)
    with SessionLocal() as db:
        results = ShopService(db, now=early).search(ShopListQuery(open_now=True))
    assert [shop.name for shop in results] == ["Meydan Kahve Kızılay", "Konya Kahve Konağı"]


@pytest.mark.parametrize(
    ("utc_hour", "rotterdam_open"),
    [
        # Kasımda Rotterdam UTC+1, Türkiye UTC+3.
        (6, False),  # Rotterdam 07:00 (08:00'de açılır), Türkiye 09:00
        (7, True),  # Rotterdam 08:00
        (16, True),  # Rotterdam 17:00
        (17, False),  # Rotterdam 18:00 (kapanış), Türkiye 20:00
    ],
)
def test_opening_hours_use_each_shops_own_timezone(shops, utc_hour, rotterdam_open):
    now = datetime(2026, 11, 20, utc_hour, 0, tzinfo=timezone.utc)
    with SessionLocal() as db:
        results = ShopService(db, now=now).search(ShopListQuery(q="rotterdam"))
    assert results[0].is_open_now is rotterdam_open


@pytest.mark.parametrize(
    "params",
    [{"lat": 39.92}, {"radius": 5}, {"sort": "distance"}, {"lat": 120, "lng": 32}, {"q": "a"}],
)
def test_invalid_location_params_are_rejected(shops, params):
    response = shops.get(SHOPS, params=params)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_shop_detail_includes_menu_and_distance(shops):
    shop_id = shops.get(SHOPS, params=KIZILAY).json()["data"][0]["id"]

    response = shops.get(f"{SHOPS}/{shop_id}", params=KIZILAY)

    assert response.status_code == 200
    detail = response.json()["data"]
    assert detail["name"] == "Meydan Kahve Kızılay"
    assert detail["phone"]
    assert detail["distance_km"] < 1
    assert detail["hours_display"] == "7/24 açık"
    assert detail["is_open_now"] is True
    categories = [item["category"] for item in detail["menu"]]
    order = ["ESPRESSO_BASED", "FILTER_COFFEE", "COLD_DRINK", "OTHER"]
    assert categories == sorted(categories, key=order.index)
    espresso = next(item for item in detail["menu"] if item["name"] == "Espresso")
    assert espresso["price_display"] == "125,00 TL"
    assert espresso["category_label"] == "Espresso Bazlı"
    labels = {item["name"]: item["category_label"] for item in detail["menu"]}
    assert labels["Iced Latte"] == "Soğuk İçecekler"
    assert labels["Türk Kahvesi"] == "Diğer"
    assert labels["Demleme Çay"] == "Diğer"


def test_filter_coffee_category(shops):
    shop_id = shops.get(SHOPS, params={"q": "tunalı"}).json()["data"][0]["id"]
    menu = shops.get(f"{SHOPS}/{shop_id}/menu").json()["data"]["products"]
    assert {p["name"] for p in menu if p["category"] == "FILTER_COFFEE"} == {"Filtre Kahve"}


def test_menu_endpoint(shops):
    shop_id = shops.get(SHOPS, params={"q": "tunalı"}).json()["data"][0]["id"]

    menu = shops.get(f"{SHOPS}/{shop_id}/menu").json()["data"]
    assert menu["shop_name"] == "Tunalı Kahve Kavurma"
    assert len(menu["products"]) == 7


def test_unknown_shop_returns_404(shops):
    response = shops.get(f"{SHOPS}/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SHOP_NOT_FOUND"
