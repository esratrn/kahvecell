import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { getErrorCode, getErrorMessage } from '../api/client'
import { listOrderHistory, reorder } from '../api/orders'
import OrderStatusBadge from '../components/OrderStatusBadge'
import { formatDateTime } from '../lib/format'
import { FINISHED_STATUSES } from '../lib/orderStatus'

const PAGE_SIZE = 20
const SUBSCRIPTION_ERRORS = ['NO_ACTIVE_SUBSCRIPTION', 'NO_CREDITS_LEFT']

export default function HistoryPage() {
  const navigate = useNavigate()
  const [orders, setOrders] = useState([])
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reorderState, setReorderState] = useState({ orderId: null, error: null })

  const loadPage = useCallback(async (offset) => {
    setLoading(true)
    setError(null)
    try {
      const page = await listOrderHistory({ offset, limit: PAGE_SIZE })
      setOrders((previous) => (offset === 0 ? page : [...previous, ...page]))
      setHasMore(page.length === PAGE_SIZE)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadPage(0)
  }, [loadPage])

  async function handleReorder(orderId) {
    setReorderState({ orderId, error: null })
    try {
      const result = await reorder(orderId)
      navigate(`/siparis/${result.order.id}`, { state: { remainingCredits: result.remaining_credits } })
    } catch (err) {
      setReorderState({ orderId, error: err })
    }
  }

  return (
    <section className="stack">
      <h1>Siparişlerim</h1>

      {error && <p className="alert error">{error}</p>}
      {loading && orders.length === 0 && <p className="muted">Siparişler yükleniyor…</p>}
      {!loading && !error && orders.length === 0 && (
        <div className="card stack center-text">
          <p className="muted">Henüz siparişin yok.</p>
          <Link className="button" to="/">
            İlk kahveni seç ☕
          </Link>
        </div>
      )}

      {orders.length > 0 && (
        <ul className="history-list">
          <li className="history-row history-head" aria-hidden="true">
            <span>Tarih</span>
            <span>Dükkân</span>
            <span>Ürün</span>
            <span>Durum</span>
            <span />
          </li>
          {orders.map((order) => {
            const isActive = !FINISHED_STATUSES.includes(order.status)
            const failed = reorderState.orderId === order.id && reorderState.error
            return (
              <li key={order.id} className="history-row">
                <span className="small" data-label="Tarih">
                  {formatDateTime(order.created_at)}
                </span>
                <span data-label="Dükkân">{order.shop.name}</span>
                <span data-label="Ürün">
                  {order.item.product_name}
                  <span className="muted small block">{order.item.summary}</span>
                </span>
                <span data-label="Durum">
                  <OrderStatusBadge status={order.status} />
                </span>
                <span className="history-actions">
                  {isActive ? (
                    <Link className="button small-button" to={`/siparis/${order.id}`}>
                      QR’ı göster
                    </Link>
                  ) : (
                    <button
                      type="button"
                      className="button secondary small-button"
                      onClick={() => handleReorder(order.id)}
                      disabled={reorderState.orderId === order.id && !reorderState.error}
                    >
                      Tekrar sipariş ver
                    </button>
                  )}
                </span>
                {failed && (
                  <p className="alert error small history-error">
                    {getErrorMessage(failed)}{' '}
                    {SUBSCRIPTION_ERRORS.includes(getErrorCode(failed)) && (
                      <Link to="/abonelik">Aboneliğe git →</Link>
                    )}
                  </p>
                )}
              </li>
            )
          })}
        </ul>
      )}

      {hasMore && (
        <button
          type="button"
          className="button secondary"
          onClick={() => loadPage(orders.length)}
          disabled={loading}
        >
          {loading ? 'Yükleniyor…' : 'Daha fazla göster'}
        </button>
      )}
    </section>
  )
}
