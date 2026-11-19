import { useState } from 'react'

import { getErrorCode, getErrorMessage } from '../../api/client'
import { changePlan } from '../../api/subscriptions'
import { formatDate, formatTry } from '../../lib/format'
import { TEST_CARD } from '../../lib/testCard'
import { toast } from '../../store/toastStore'
import CardFields from '../CardFields'
import Modal from '../Modal'

export default function PlanChangeModal({ subscription, plan, holderName, onClose, onChanged }) {
  const current = subscription.plan
  const isUpgrade = plan.price_kurus > current.price_kurus
  // Kayıtlı kart yoksa (örn. örnek verideki abonelik) yükseltmede kart istenir.
  const needsCard = isUpgrade && !subscription.card_last4

  const [card, setCard] = useState({ ...TEST_CARD, holder_name: holderName ?? '' })
  const [submitting, setSubmitting] = useState(false)
  const [inlineError, setInlineError] = useState(null)

  const difference = plan.price_kurus - current.price_kurus
  const extraCredits = plan.is_unlimited ? null : plan.monthly_credits - current.monthly_credits

  async function handleConfirm(event) {
    event.preventDefault()
    setInlineError(null)
    setSubmitting(true)
    try {
      const result = await changePlan(plan.code, needsCard ? card : null)
      toast.success(result.message)
      onChanged()
    } catch (err) {
      setSubmitting(false)
      if (getErrorCode(err) === 'PAYMENT_FAILED') {
        toast.error(getErrorMessage(err))
        onClose()
      } else {
        setInlineError(getErrorMessage(err))
      }
    }
  }

  return (
    <Modal
      title={isUpgrade ? `${plan.name} paketine yükselt` : `${plan.name} paketine geç`}
      onClose={onClose}
      busy={submitting}
    >
      <form className="stack" onSubmit={handleConfirm}>
        {isUpgrade ? (
          <>
            <p>
              {current.name} → <strong>{plan.name}</strong>. Yükseltme hemen geçerli olur; yalnızca iki paket
              arasındaki fark alınır.
            </p>
            <p className="payment-summary">
              <span>Fark ücreti</span>
              <strong>{formatTry(difference)}</strong>
            </p>
            <p className="muted small">
              {extraCredits === null
                ? 'Kredi sınırın kalkacak.'
                : `Mevcut kredilerine +${extraCredits} kredi eklenecek.`}
            </p>
            {needsCard ? (
              <CardFields value={card} onChange={setCard} disabled={submitting} />
            ) : (
              <p className="small">Kayıtlı kartından (•••• {subscription.card_last4}) tahsil edilecek.</p>
            )}
          </>
        ) : (
          <p>
            {formatDate(subscription.expires_at)} tarihine kadar {current.name} paketin geçerli kalır; sonraki
            dönemden itibaren <strong>{plan.name}</strong> paketine geçilir. Şu an ödeme alınmaz.
          </p>
        )}

        {inlineError && <p className="alert error">{inlineError}</p>}
        <button type="submit" className="button" disabled={submitting}>
          {submitting ? 'İşleniyor…' : isUpgrade ? `${formatTry(difference)} öde ve yükselt` : 'Onayla'}
        </button>
      </form>
    </Modal>
  )
}
