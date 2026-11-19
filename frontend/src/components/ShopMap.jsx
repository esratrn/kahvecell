import { useEffect } from 'react'
import { CircleMarker, MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import { Link } from 'react-router-dom'

import { ANKARA_KIZILAY } from '../lib/leaflet'

const USER_MARKER_STYLE = { color: '#ffffff', weight: 3, fillColor: '#d9822b', fillOpacity: 1 }
const NEARBY_KM = 50

// Harita yakındaki dükkânlara odaklanır; Ankara'dayken Rotterdam yüzünden Avrupa'ya uzaklaşmaz.
function focusPoints(shops, userLocation) {
  const nearby = shops.filter((shop) => shop.distance_km != null && shop.distance_km <= NEARBY_KM)
  const focused = nearby.length > 0 ? nearby : shops
  const points = focused.map((shop) => [shop.latitude, shop.longitude])
  if (userLocation && (nearby.length > 0 || shops.length === 0)) {
    points.push(userLocation)
  }
  return points
}

function FitToPoints({ points }) {
  const map = useMap()
  const key = JSON.stringify(points)

  useEffect(() => {
    const parsed = JSON.parse(key)
    if (parsed.length === 1) {
      map.setView(parsed[0], 15)
    } else if (parsed.length > 1) {
      map.fitBounds(parsed, { padding: [40, 40], maxZoom: 15 })
    }
  }, [map, key])

  return null
}

export default function ShopMap({ shops, userLocation, userLabel = 'Buradasın' }) {
  const points = focusPoints(shops, userLocation)

  return (
    <MapContainer center={userLocation ?? ANKARA_KIZILAY} zoom={13} className="map">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitToPoints points={points} />

      {shops.map((shop) => (
        <Marker key={shop.id} position={[shop.latitude, shop.longitude]}>
          <Popup>
            <strong>{shop.name}</strong>
            <br />
            {shop.address}
            <br />
            <Link to={`/dukkan/${shop.id}`}>Menüyü gör</Link>
          </Popup>
        </Marker>
      ))}

      {userLocation && (
        <CircleMarker center={userLocation} radius={9} pathOptions={USER_MARKER_STYLE}>
          <Popup>{userLabel}</Popup>
        </CircleMarker>
      )}
    </MapContainer>
  )
}
