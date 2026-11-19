import { useState } from 'react'

import { getErrorCode, getErrorMessage } from '../../api/client'
import { subscribe } from '../../api/subscriptions'
import { TEST_CARD } from '../../lib/testCard'
import { toast } from '../../store/toastStore'
import CardFields from '../CardFields'
import Modal from '../Modal'

export default function PurchaseModal({ plan, holderName, onClose, onPurchased }) {
  const [card, setCard] = useState({ ...TEST_CARD, holder_name: holderName ?? '' })
  const [submitting, setSubmitting] = useState(false)
  const [inlineError, setInlineError] = useState(null)

  async function handleSubmit(event) {
    event.preventDefault()
    setInlineError(null)
    setSubmitting(true)
    try {
      const result = await subscribe(plan.code, card)
      toast.success(
        `Ödeme başarılı! ${plan.name} paketin aktif. İşlem no: ${result.payment.transaction_id}`,
      )
      onPurchased()
    } catch (err) {
      setSubmitting(false)
      if (getErrorCode(err) === 'PAYMENT_FAILED') {
        // Ödeme denendi ve reddedildi: pencere kapanır, sonuç bildirimle söylenir.
        toast.error(getErrorMessage(err))
        onClose()
      } else {
        // Form hatası (geçersiz kart vb.): kullanıcı düzeltebilsin diye pencerede kalır.
        setInlineError(getErrorMessage(err))
      }
    }
  }

  return (
    <Modal title={`${plan.name} paketini satın al`} onClose={onClose} busy={submitting}>
      <p className="payment-summary">
        <span>Aylık ücret</span>
        <strong>{plan.price_display}</strong>
      </p>
      <form className="stack" onSubmit={handleSubmit}>
        <CardFields value={card} onChange={setCard} disabled={submitting} />
        {inlineError && <p className="alert error">{inlineError}</p>}
        <button type="submit" className="button" disabled={submitting}>
          {submitting ? 'Ödeme işleniyor…' : `${plan.price_display} öde`}
        </button>
        <p className="muted small center-text">Ödeme simülasyondur; gerçek bir tahsilat yapılmaz.</p>
      </form>
    </Modal>
  )
}
