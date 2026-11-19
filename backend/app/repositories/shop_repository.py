import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Product, Shop
from app.services.geo import BoundingBox


class ShopRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_active(self, *, within: BoundingBox | None = None) -> Sequence[Shop]:
        query = select(Shop).where(Shop.is_active.is_(True))
        if within is not None:
            query = query.where(
                Shop.latitude.between(within.min_lat, within.max_lat),
                Shop.longitude.between(within.min_lng, within.max_lng),
            )
        return self.db.scalars(query).all()

    def get_active(self, shop_id: uuid.UUID) -> Shop | None:
        return self.db.scalar(select(Shop).where(Shop.id == shop_id, Shop.is_active.is_(True)))

    def list_menu(self, shop_id: uuid.UUID) -> Sequence[Product]:
        return self.db.scalars(select(Product).where(Product.shop_id == shop_id)).all()
