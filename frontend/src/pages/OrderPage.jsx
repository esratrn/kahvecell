import { useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'

import { getErrorCode, getErrorMessage } from '../api/client'
import { placeOrder } from '../api/orders'
import { getShop } from '../api/shops'
import { getMySubscription } from '../api/subscriptions'
import OptionGroup from '../components/OptionGroup'
import {
  EXTRA_SHOT_OPTIONS,
  MILK_OPTIONS,
  SIZE_OPTIONS,
  SUGAR_OPTIONS,
  describeCustomization,
} from '../lib/orderOptions'
import { useRequest } from '../lib/useRequest'

const SUBSCRIPTION_ERRORS = ['NO_ACTIVE_SUBSCRIPTION', 'NO_CREDITS_LEFT']

// Siparişi engelleyen durum varsa kullanıcıya ne yapması gerektiğini söyler.
function getBlocker({ shop, product, subscription }) {
  if (!subscription) {
    return {
      message: 'Sipariş verebilmek için aktif bir aboneliğin olmalı.',
      action: { to: '/abonelik', label: 'Abonelik al' },
    }
  }
  if (subscription.remaining_credits === 0) {
    return {
      message: 'Bu dönemki kahve kredin bitti. Paketini yükselterek hemen devam edebilirsin.',
      action: { to: '/abonelik', label: 'Paketini yükselt' },
    }
  }
  if (!shop.is_open_now) {
    return { message: `${shop.name} şu an kapalı (${shop.hours_display}).` }
  }
  if (!product.is_available) {
    return { message: `${product.name} şu an hazırlanamıyor.` }
  }
  return null
}

function CreditInfo({ subscription }) {
  if (!subscription) {
    return null
  }
  if (subscription.remaining_credits === null) {
    return (
      <div className="credit-box">
        <span>{subscription.plan.name} paketi</span>
        <strong>Sınırsız ☕</strong>
        <span className="muted small">Bu sipariş kredinden düşmez.</span>
      </div>
    )
  }
  const remaining = subscription.remaining_credits
  return (
    <div className="credit-box">
      <span>
        {subscription.plan.name} paketi · kalan kredin <strong>{remaining}</strong>
      </span>
      {remaining > 0 && (
        <span className="muted small">
          Bu sipariş sonrası <strong>{remaining - 1}</strong> kredin kalacak.
        </span>
      )}
    </div>
  )
}

export default function OrderPage() {
  const { shopId } = useParams()
  const [searchParams] = useSearchParams()
  const productId = searchParams.get('urun')
  const navigate = useNavigate()

  const shopRequest = useRequest(() => getShop(shopId), [shopId])
  const subscriptionRequest = useRequest(getMySubscription, [])

  const [size, setSize] = useState('M')
  const [sugarLevel, setSugarLevel] = useState(0)
  const [milk, setMilk] = useState('NONE')
  const [extraShots, setExtraShots] = useState(0)
  const [note, setNote] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  if (shopRequest.loading || subscriptionRequest.loading) {
    return <p className="muted">Yükleniyor…</p>
  }
  if (shopRequest.error || subscriptionRequest.error) {
    return <p className="alert error">{getErrorMessage(shopRequest.error ?? subscriptionRequest.error)}</p>
  }

  const shop = shopRequest.data
  const subscription = subscriptionRequest.data
  const product = shop.menu.find((item) => item.id === productId)

  if (!product) {
    return (
      <section className="stack narrow-page">
        <p className="alert error">Bu ürün {shop.name} menüsünde bulunamadı.</p>
        <Link to={`/dukkan/${shop.id}`}>← Menüden bir ürün seç</Link>
      </section>
    )
  }

  const blocker = getBlocker({ shop, product, subscription })

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const result = await placeOrder({
        shop_id: shop.id,
        product_id: product.id,
        size,
        sugar_level: sugarLevel,
        milk,
        extra_shots: extraShots,
        note: note.trim() || null,
      })
      navigate(`/siparis/${result.order.id}`, { state: { remainingCredits: result.remaining_credits } })
    } catch (err) {
      setError(err)
      setSubmitting(false)
      if (SUBSCRIPTION_ERRORS.includes(getErrorCode(err))) {
        // Kredi başka bir cihazda bitmiş olabilir; ekrandaki bilgi güncellensin.
        subscriptionRequest.reload({ silent: true })
      }
    }
  }

  return (
    <section className="stack narrow-page">
      <Link to={`/dukkan/${shop.id}`}>← {shop.name} menüsü</Link>

      <div className="card product-hero">
        <span className="badge">{product.category_label}</span>
        <h1>{product.name}</h1>
        {product.description && <p className="muted">{product.description}</p>}
        <p className="small muted">
          {shop.name} · liste fiyatı {product.price_display}
        </p>
      </div>

      <CreditInfo subscription={subscription} />

      <form className="card stack" onSubmit={handleSubmit}>
        <h2>Kahveni özelleştir</h2>
        <OptionGroup name="size" label="Boy" options={SIZE_OPTIONS} value={size} onChange={setSize} />
        <label className="field">
          Süt tipi
          <select value={milk} onChange={(event) => setMilk(event.target.value)}>
            {MILK_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <OptionGroup
          name="sugar"
          label="Şeker"
          options={SUGAR_OPTIONS}
          value={sugarLevel}
          onChange={setSugarLevel}
        />
        <OptionGroup
          name="shots"
          label="Ek shot"
          options={EXTRA_SHOT_OPTIONS}
          value={extraShots}
          onChange={setExtraShots}
        />
        <label className="field">
          Not (isteğe bağlı)
          <input
            maxLength={255}
            placeholder="Örn. bardağa isim: Esra"
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />
        </label>

        <p className="summary">
          <strong>{product.name}</strong> ·{' '}
          {describeCustomization({ size, milk, sugar_level: sugarLevel, extra_shots: extraShots })}
        </p>

        {blocker && (
          <div className="alert error stack">
            <span>{blocker.message}</span>
            {blocker.action && (
              <Link className="button" to={blocker.action.to}>
                {blocker.action.label} →
              </Link>
            )}
          </div>
        )}
        {error && !blocker && <p className="alert error">{getErrorMessage(error)}</p>}

        <button type="submit" className="button" disabled={Boolean(blocker) || submitting}>
          {submitting ? 'Sipariş veriliyor…' : 'Siparişi onayla'}
        </button>
      </form>
    </section>
  )
}
