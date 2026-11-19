import { useEffect, useState } from 'react'

import { getErrorMessage } from '../api/client'
import { listShops } from '../api/shops'
import ShopCard from '../components/ShopCard'
import ShopMap from '../components/ShopMap'
import { useDebouncedValue } from '../lib/useDebouncedValue'
import { useRequest } from '../lib/useRequest'
import { useLocationStore } from '../store/locationStore'
import { useAuthStore } from '../store/authStore'

const MIN_QUERY_LENGTH = 2
const FAR_AWAY_KM = 50

const LOCATION_MESSAGES = {
  idle: 'Konumun alınıyor…',
  locating: 'Konumun alınıyor…',
  granted: 'Dükkânlar sana olan uzaklığa göre sıralandı.',
  denied: "Konum izni verilmedi; mesafeler Kızılay'a göre gösteriliyor.",
  unavailable: "Konumun alınamadı; mesafeler Kızılay'a göre gösteriliyor.",
}

export default function HomePage() {
  const user = useAuthStore((state) => state.user)
  const { coords, status, requestLocation } = useLocationStore()
  const [lat, lng] = coords

  const [query, setQuery] = useState('')
  const debouncedQuery = useDebouncedValue(query.trim())
  const search = debouncedQuery.length >= MIN_QUERY_LENGTH ? debouncedQuery : undefined

  useEffect(() => {
    requestLocation()
  }, [requestLocation])

  const { data: shops, error, loading } = useRequest(
    () => listShops({ lat, lng, q: search }),
    [lat, lng, search],
  )

  const isDeviceLocation = status === 'granted'
  const nearest = shops?.[0]
  const firstName = user?.full_name?.split(' ')[0]

  return (
    <section className="stack">
      <div>
        <h1>{firstName ? `Hoş geldin, ${firstName} ☕` : 'Yakındaki kahveciler ☕'}</h1>
        <p className="muted small">{LOCATION_MESSAGES[status]}</p>
      </div>

      <div className="home-grid">
        <div className="stack">
          <label className="field">
            <span className="visually-hidden">Dükkân ara</span>
            <input
              type="search"
              placeholder="Dükkân, semt, cadde veya şehir ara…"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>

          {error && <p className="alert error">{getErrorMessage(error)}</p>}
          {loading && !shops && <p className="muted">Dükkânlar yükleniyor…</p>}
          {isDeviceLocation && nearest && nearest.distance_km > FAR_AWAY_KM && !search && (
            <p className="alert info">
              Yakınında anlaşmalı dükkân yok; en yakını {nearest.distance_display} uzakta.
            </p>
          )}
          {shops && shops.length === 0 && (
            <p className="muted">
              {search ? `“${search}” için dükkân bulunamadı.` : 'Henüz anlaşmalı dükkân yok.'}
            </p>
          )}

          {shops && shops.length > 0 && (
            <ul className="shop-list" aria-busy={loading}>
              {shops.map((shop) => (
                <li key={shop.id}>
                  <ShopCard shop={shop} />
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="map-column">
          <ShopMap
            shops={shops ?? []}
            userLocation={coords}
            userLabel={isDeviceLocation ? 'Buradasın' : 'Varsayılan konum: Kızılay'}
          />
        </div>
      </div>
    </section>
  )
}
