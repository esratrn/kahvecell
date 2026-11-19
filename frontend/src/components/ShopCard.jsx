import { Link } from 'react-router-dom'

import StatusBadge from './StatusBadge'

export default function ShopCard({ shop }) {
  return (
    <article className="shop-card">
      <div className="row spread">
        <h2 className="shop-card-title">{shop.name}</h2>
        <StatusBadge tone={shop.is_open_now ? 'success' : 'neutral'}>
          {shop.is_open_now ? 'Açık' : 'Kapalı'}
        </StatusBadge>
      </div>
      <p className="muted small">
        {shop.address}, {shop.district} / {shop.city}
      </p>
      <div className="row spread">
        <p className="row small">
          <span>⭐ {shop.rating}</span>
          {shop.distance_display && <span>📍 {shop.distance_display}</span>}
        </p>
        <Link className="button small-button" to={`/dukkan/${shop.id}`}>
          Menüyü Gör
        </Link>
      </div>
    </article>
  )
}
