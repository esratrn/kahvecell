import math
from dataclasses import dataclass
from datetime import time

EARTH_RADIUS_KM = 6371.0088
_KM_PER_DEGREE_LAT = 111.32


@dataclass(frozen=True)
class BoundingBox:
    min_lat: float
    max_lat: float
    min_lng: float
    max_lng: float


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def bounding_box(lat: float, lng: float, radius_km: float) -> BoundingBox:
    # Veritabanında indeksli kaba bir ön eleme için; kesin mesafe Haversine ile hesaplanır.
    lat_delta = radius_km / _KM_PER_DEGREE_LAT
    lng_delta = radius_km / (_KM_PER_DEGREE_LAT * max(math.cos(math.radians(lat)), 1e-6))
    return BoundingBox(lat - lat_delta, lat + lat_delta, lng - lng_delta, lng + lng_delta)


def format_distance(distance_km: float) -> str:
    if distance_km < 1:
        return f"{max(10, round(distance_km * 100) * 10)} m"
    if distance_km >= 100:
        return f"{round(distance_km):,} km".replace(",", ".")
    return f"{distance_km:.1f} km".replace(".", ",")


def is_open_at(opening: time, closing: time, at: time) -> bool:
    if opening == closing:
        return True
    if opening < closing:
        return opening <= at < closing
    # Gece yarısını geçen saatler (örn. 18:00–02:00).
    return at >= opening or at < closing
