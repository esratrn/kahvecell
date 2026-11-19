import { useEffect } from 'react'
import { Link, useParams } from 'react-router-dom'

import { getErrorMessage } from '../api/client'
import { getShop } from '../api/shops'
import ShopMap from '../components/ShopMap'
import StatusBadge from '../components/StatusBadge'
import { useRequest } from '../lib/useRequest'
import { useLocationStore } from '../store/locationStore'

function groupByCategory(menu) {
  const groups = new Map()
  for (const product of menu) {
    if (!groups.has(product.category_label)) {
      groups.set(product.category_label, [])
    }
    groups.get(product.category_label).push(product)
  }
  return [...groups.entries()]
}

export default function ShopDetailPage() {
  const { shopId } = useParams()
  const { coords, status, requestLocation } = useLocationStore()
  const [lat, lng] = coords
  const { data: shop, error, loading } = useRequest(() => getShop(shopId, { lat, lng }), [shopId, lat, lng])

  useEffect(() => {
    requestLocation()
  }, [requestLocation])

  if (loading && !shop) {
    return <p className="muted">Dükkân yükleniyor…</p>
  }
  if (error) {
    return (
      <div className="stack">
        <p className="alert error">{getErrorMessage(error)}</p>
        <Link to="/">← Dükkânlara dön</Link>
      </div>
    )
  }

  return (
    <section className="stack">
      <Link to="/">← Dükkânlar</Link>

      <div className="card stack">
        <div className="row spread">
          <h1>{shop.name}</h1>
          <StatusBadge tone={shop.is_open_now ? 'success' : 'neutral'}>
            {shop.is_open_now ? 'Şu an açık' : 'Şu an kapalı'}
          </StatusBadge>
        </div>
        <p className="muted">
          {shop.address}, {shop.district} / {shop.city}
        </p>
        <p className="row">
          <span>⭐ {shop.rating} ({shop.rating_count} değerlendirme)</span>
          {shop.distance_display && <span>📍 {shop.distance_display}</span>}
          <span>🕒 {shop.hours_display}</span>
          {shop.phone && <span>📞 {shop.phone}</span>}
        </p>
        {shop.description && <p>{shop.description}</p>}
      </div>

      <ShopMap
        shops={[shop]}
        userLocation={coords}
        userLabel={status === 'granted' ? 'Buradasın' : 'Varsayılan konum: Kızılay'}
      />

      <h2>Menü</h2>
      {!shop.is_open_now && (
        <p className="alert info">Dükkân şu an kapalı; menüyü görebilir, açılış saatinde sipariş verebilirsin.</p>
      )}
      {shop.menu.length === 0 && <p className="muted">Bu dükkânın menüsü henüz eklenmemiş.</p>}
      {groupByCategory(shop.menu).map(([category, products]) => (
        <div key={category} className="stack">
          <h3>{category}</h3>
          <ul className="list">
            {products.map((product) => {
              const canOrder = shop.is_open_now && product.is_available
              return (
                <li key={product.id} className="list-item">
                  <div>
                    <strong>{product.name}</strong>
                    <p className="muted small">{product.description}</p>
                  </div>
                  <div className="row">
                    <span className="muted small">Liste fiyatı {product.price_display}</span>
                    {canOrder ? (
                      <Link className="button" to={`/dukkan/${shop.id}/siparis?urun=${product.id}`}>
                        Sipariş Ver
                      </Link>
                    ) : (
                      <button type="button" className="button" disabled>
                        {product.is_available ? 'Kapalı' : 'Tükendi'}
                      </button>
                    )}
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      ))}
    </section>
  )
}
