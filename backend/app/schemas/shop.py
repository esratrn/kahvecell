import uuid
from datetime import time
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.core.money import format_try
from app.models import Product, ProductCategory, Shop
from app.services.geo import format_distance

CATEGORY_LABELS = {
    ProductCategory.ESPRESSO_BASED: "Espresso Bazlı",
    ProductCategory.FILTER_COFFEE: "Filtre Kahveler",
    ProductCategory.COLD_DRINK: "Soğuk İçecekler",
    ProductCategory.OTHER: "Diğer",
}


class ShopSort(StrEnum):
    DISTANCE = "distance"
    RATING = "rating"
    NAME = "name"


class ShopListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    lat: float | None = Field(None, ge=-90, le=90, description="Kullanıcının enlemi")
    lng: float | None = Field(None, ge=-180, le=180, description="Kullanıcının boylamı")
    radius: float | None = Field(None, gt=0, le=100, description="Arama yarıçapı (km)")
    q: str | None = Field(None, min_length=2, max_length=100, description="İsim veya adreste ara")
    min_rating: float | None = Field(None, ge=0, le=5, description="En düşük puan")
    open_now: bool = Field(False, description="Sadece şu an açık olanlar")
    sort: ShopSort | None = Field(
        None, description="Varsayılan: konum varsa mesafe, yoksa puan"
    )
    offset: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)

    @model_validator(mode="after")
    def _check_location_params(self) -> "ShopListQuery":
        if (self.lat is None) != (self.lng is None):
            raise ValueError("lat ve lng birlikte gönderilmelidir.")
        if self.lat is None and (self.radius is not None or self.sort == ShopSort.DISTANCE):
            raise ValueError("radius ve sort=distance için lat ve lng gereklidir.")
        return self

    @property
    def has_location(self) -> bool:
        return self.lat is not None and self.lng is not None


class ShopSummary(BaseModel):
    id: uuid.UUID
    name: str
    address: str
    district: str | None
    city: str
    latitude: float
    longitude: float
    rating: float
    rating_count: int
    image_url: str | None
    opening_time: time
    closing_time: time
    is_open_now: bool
    # Konum gönderilmediyse null.
    distance_km: float | None

    @computed_field
    @property
    def hours_display(self) -> str:
        if self.opening_time == self.closing_time:
            return "7/24 açık"
        return f"{self.opening_time:%H:%M}–{self.closing_time:%H:%M}"

    @computed_field
    @property
    def distance_display(self) -> str | None:
        return None if self.distance_km is None else format_distance(self.distance_km)

    @classmethod
    def build(cls, shop: Shop, *, is_open_now: bool, distance_km: float | None) -> "ShopSummary":
        return cls(
            id=shop.id,
            name=shop.name,
            address=shop.address,
            district=shop.district,
            city=shop.city,
            latitude=shop.latitude,
            longitude=shop.longitude,
            rating=shop.rating,
            rating_count=shop.rating_count,
            image_url=shop.image_url,
            opening_time=shop.opening_time,
            closing_time=shop.closing_time,
            is_open_now=is_open_now,
            distance_km=None if distance_km is None else round(distance_km, 2),
        )


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    category: ProductCategory
    price_kurus: int
    image_url: str | None
    is_available: bool

    @computed_field
    @property
    def category_label(self) -> str:
        return CATEGORY_LABELS[self.category]

    @computed_field
    @property
    def price_display(self) -> str:
        return format_try(self.price_kurus)


class MenuOut(BaseModel):
    shop_id: uuid.UUID
    shop_name: str
    products: list[ProductOut]

    @classmethod
    def build(cls, shop: Shop, products: list[Product]) -> "MenuOut":
        return cls(
            shop_id=shop.id,
            shop_name=shop.name,
            products=[ProductOut.model_validate(p) for p in products],
        )


class ShopDetail(ShopSummary):
    description: str | None
    phone: str | None
    menu: list[ProductOut]
