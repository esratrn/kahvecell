import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.core.responses import ApiResponse, ok
from app.schemas.shop import MenuOut, ShopDetail, ShopListQuery, ShopSummary
from app.services.shop_service import ShopService

router = APIRouter(prefix="/shops", tags=["Shops"])


@router.get(
    "",
    response_model=ApiResponse[list[ShopSummary]],
    summary="Dükkânları listele / yakındakileri bul / ara",
    description=(
        "Parametresiz çağrı tüm dükkânları puana göre getirir. lat+lng gönderilirse her dükkânın "
        "mesafesi hesaplanır ve en yakından uzağa sıralanır; radius (km) ile alan daraltılır. "
        "q isim, adres ve semtte arar (Türkçe karakterli/karaktersiz yazım fark etmez)."
    ),
)
def list_shops(query: Annotated[ShopListQuery, Query()], db: DbSession):
    return ok(ShopService(db).search(query))


@router.get(
    "/{shop_id}",
    response_model=ApiResponse[ShopDetail],
    summary="Dükkân detayı ve menüsü",
    description="lat+lng gönderilirse dükkâna olan mesafe de döner.",
)
def get_shop(
    shop_id: uuid.UUID,
    db: DbSession,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lng: Annotated[float | None, Query(ge=-180, le=180)] = None,
):
    return ok(ShopService(db).get_detail(shop_id, lat, lng))


@router.get("/{shop_id}/menu", response_model=ApiResponse[MenuOut], summary="Dükkân menüsü")
def get_menu(shop_id: uuid.UUID, db: DbSession):
    return ok(ShopService(db).get_menu(shop_id))
