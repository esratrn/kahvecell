import uuid
from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.text import normalize_tr
from app.models import Product, ProductCategory, Shop
from app.models.base import utcnow
from app.repositories.shop_repository import ShopRepository
from app.schemas.shop import MenuOut, ShopDetail, ShopListQuery, ShopSort, ShopSummary
from app.services.geo import bounding_box, haversine_km, is_open_at

_CATEGORY_ORDER = {category: index for index, category in enumerate(ProductCategory)}


@lru_cache
def _zone(name: str) -> ZoneInfo:
    return ZoneInfo(name)


def is_shop_open(shop: Shop, now: datetime) -> bool:
    # Çalışma saatleri dükkânın kendi saat dilimindedir (Rotterdam'da 09:00, İstanbul'da 11:00'dir).
    local_time = now.astimezone(_zone(shop.timezone)).time()
    return is_open_at(shop.opening_time, shop.closing_time, local_time)


def _matches(shop: Shop, terms: list[str]) -> bool:
    haystack = normalize_tr(" ".join(filter(None, [shop.name, shop.address, shop.district, shop.city])))
    return all(term in haystack for term in terms)


def _sorted_menu(products: list[Product]) -> list[Product]:
    return sorted(products, key=lambda p: (_CATEGORY_ORDER[p.category], p.price_kurus, p.name))


class ShopService:
    def __init__(self, db: Session, now: datetime | None = None) -> None:
        self.shops = ShopRepository(db)
        self.now = now or utcnow()

    def search(self, query: ShopListQuery) -> list[ShopSummary]:
        within = None
        if query.has_location and query.radius is not None:
            within = bounding_box(query.lat, query.lng, query.radius)
        terms = normalize_tr(query.q).split() if query.q else []

        results: list[ShopSummary] = []
        for shop in self.shops.list_active(within=within):
            distance = (
                haversine_km(query.lat, query.lng, shop.latitude, shop.longitude)
                if query.has_location
                else None
            )
            if query.radius is not None and distance > query.radius:
                continue
            if terms and not _matches(shop, terms):
                continue
            if query.min_rating is not None and shop.rating < query.min_rating:
                continue
            is_open = is_shop_open(shop, self.now)
            if query.open_now and not is_open:
                continue
            results.append(ShopSummary.build(shop, is_open_now=is_open, distance_km=distance))

        sort = query.sort or (ShopSort.DISTANCE if query.has_location else ShopSort.RATING)
        if sort == ShopSort.DISTANCE:
            results.sort(key=lambda s: s.distance_km)
        elif sort == ShopSort.RATING:
            results.sort(key=lambda s: (-s.rating, -s.rating_count))
        else:
            results.sort(key=lambda s: normalize_tr(s.name))
        return results[query.offset : query.offset + query.limit]

    def get_detail(self, shop_id: uuid.UUID, lat: float | None, lng: float | None) -> ShopDetail:
        shop = self._get_shop(shop_id)
        distance = None
        if lat is not None and lng is not None:
            distance = haversine_km(lat, lng, shop.latitude, shop.longitude)
        summary = ShopSummary.build(
            shop,
            is_open_now=is_shop_open(shop, self.now),
            distance_km=distance,
        )
        menu = MenuOut.build(shop, _sorted_menu(list(self.shops.list_menu(shop.id))))
        return ShopDetail(
            **summary.model_dump(exclude={"hours_display", "distance_display"}),
            description=shop.description,
            phone=shop.phone,
            menu=menu.products,
        )

    def get_menu(self, shop_id: uuid.UUID) -> MenuOut:
        shop = self._get_shop(shop_id)
        return MenuOut.build(shop, _sorted_menu(list(self.shops.list_menu(shop.id))))

    def _get_shop(self, shop_id: uuid.UUID) -> Shop:
        shop = self.shops.get_active(shop_id)
        if shop is None:
            raise NotFoundError("Dükkân bulunamadı.", code="SHOP_NOT_FOUND")
        return shop
