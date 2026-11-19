import { useEffect, useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { Link, useLocation, useParams } from 'react-router-dom'

import { getErrorMessage } from '../api/client'
import { cancelOrder, getOrder } from '../api/orders'
import { formatTime } from '../lib/format'
import { FINISHED_STATUSES, ORDER_STATUS, STATUS_FLOW } from '../lib/orderStatus'
import { useRequest } from '../lib/useRequest'

const POLL_INTERVAL_MS = 4000

function StatusStepper({ status }) {
  const currentIndex = STATUS_FLOW.indexOf(status)
  return (
    <ol className="stepper" aria-label="Sipariş aşamaları">
      {STATUS_FLOW.map((step, index) => {
        const state = index < currentIndex ? 'done' : index === currentIndex ? 'current' : ''
        return (
          <li key={step} className={state} aria-current={state === 'current' ? 'step' : undefined}>
            <span className="dot" />
            <span className="small">{ORDER_STATUS[step].label}</span>
          </li>
        )
      })}
    </ol>
  )
}

function EnjoyMessage({ order }) {
  return (
    <div className="enjoy">
      <div className="enjoy-cup" aria-hidden="true">
        ☕
      </div>
      <h2>Afiyet olsun!</h2>
      <p className="muted">
        {order.item.product_name} siparişin {formatTime(order.completed_at)}’de {order.shop.name} dükkânında
        teslim edildi.
      </p>
      <div className="row center">
        <Link className="button" to="/">
          Yeni kahve
        </Link>
        <Link className="button secondary" to="/gecmis">
          Siparişlerim
        </Link>
      </div>
    </div>
  )
}

export default function QrPage() {
  const { orderId } = useParams()
  const location = useLocation()
  const remainingCredits = location.state?.remainingCredits
  const { data: order, error, loading, reload } = useRequest(() => getOrder(orderId), [orderId])
  const [cancelError, setCancelError] = useState(null)
  const [cancelling, setCancelling] = useState(false)

  const status = order?.status
  const isActive = Boolean(status) && !FINISHED_STATUSES.includes(status)

  useEffect(() => {
    if (!isActive) {
      return undefined
    }
    const timer = setInterval(() => {
      // Sekme arka plandayken sunucu boşuna yorulmasın.
      if (!document.hidden) {
        reload({ silent: true })
      }
    }, POLL_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [isActive, reload])

  useEffect(() => {
    if (!status) {
      return undefined
    }
    // Kullanıcı başka sekmedeyken de durumu sekme başlığından görebilir.
    document.title = `${ORDER_STATUS[status].icon} ${ORDER_STATUS[status].label} · KahveCell`
    return () => {
      document.title = 'KahveCell'
    }
  }, [status])

  async function handleCancel() {
    setCancelError(null)
    setCancelling(true)
    try {
      await cancelOrder(orderId)
      await reload({ silent: true })
    } catch (err) {
      setCancelError(getErrorMessage(err))
    } finally {
      setCancelling(false)
    }
  }

  if (loading && !order) {
    return <p className="muted">Sipariş yükleniyor…</p>
  }
  if (error) {
    return (
      <div className="stack narrow-page">
        <p className="alert error">{getErrorMessage(error)}</p>
        <Link to="/gecmis">← Siparişlerim</Link>
      </div>
    )
  }

  const meta = ORDER_STATUS[order.status]

  return (
    <section className={`qr-page stack narrow-page tone-${meta.tone}`}>
      {remainingCredits !== undefined && order.status === 'PENDING' && (
        <p className="alert info">
          Siparişin alındı.{' '}
          {remainingCredits === null ? 'Sınırsız paketindesin.' : `Kalan kahve kredin: ${remainingCredits}.`}
        </p>
      )}

      {order.status === 'COMPLETED' && <EnjoyMessage order={order} />}

      {order.qr_payload && (
        <div className="qr-frame">
          <QRCodeSVG
            value={order.qr_payload}
            size={280}
            level="M"
            marginSize={2}
            title="Sipariş QR kodu"
            className="qr-code"
          />
          <p className="muted small">Teslim alırken bu kodu dükkâna göster.</p>
        </div>
      )}

      {order.status !== 'COMPLETED' && (
        // key: durum değişince panel yeniden çizilir ve küçük bir animasyonla dikkat çeker.
        <div key={order.status} className="status-panel" role="status" aria-live="polite">
          <span className="status-icon" aria-hidden="true">
            {meta.icon}
          </span>
          <strong className="status-label">{meta.label}</strong>
          <span className="small">{meta.hint}</span>
        </div>
      )}

      {order.status !== 'CANCELLED' && <StatusStepper status={order.status} />}

      <div className="card stack">
        <div>
          <strong>{order.item.product_name}</strong>
          <p className="muted small">{order.item.summary}</p>
          {order.note && <p className="small">Not: {order.note}</p>}
        </div>
        <div>
          <strong>{order.shop.name}</strong>
          <p className="muted small">{order.shop.address}</p>
        </div>
      </div>

      {order.status === 'PENDING' && (
        <div className="stack">
          {cancelError && <p className="alert error">{cancelError}</p>}
          <button type="button" className="button secondary" onClick={handleCancel} disabled={cancelling}>
            {cancelling ? 'İptal ediliyor…' : 'Siparişi iptal et'}
          </button>
          <p className="muted small center-text">Dükkân kabul edene kadar iptal edebilirsin; kredin geri yüklenir.</p>
        </div>
      )}

      {isActive && <p className="muted small center-text">Durum her birkaç saniyede bir otomatik güncellenir.</p>}

      {order.status !== 'COMPLETED' && (
        <div className="row center">
          <Link to="/gecmis">Siparişlerim</Link>
          <Link to="/">Dükkânlar</Link>
        </div>
      )}
    </section>
  )
}
