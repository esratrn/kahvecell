import { useState } from 'react'

import { getErrorMessage } from '../../api/client'
import { cancelSubscription } from '../../api/subscriptions'
import { formatDate } from '../../lib/format'
import { toast } from '../../store/toastStore'

export default function CurrentSubscription({ subscription, onChanged }) {
  const [confirming, setConfirming] = useState(false)
  const [cancelling, setCancelling] = useState(false)

  if (!subscription) {
    return (
      <div className="card current-sub empty">
        <h2>Aktif aboneliğiniz yok</h2>
        <p className="muted">Aşağıdaki paketlerden birini seçerek hemen kahve siparişi vermeye başlayabilirsin.</p>
      </div>
    )
  }

  async function handleCancel() {
    setCancelling(true)
    try {
      const result = await cancelSubscription()
      toast.success(result.message)
      setConfirming(false)
      onChanged()
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setCancelling(false)
    }
  }

  const unlimited = subscription.remaining_credits === null

  return (
    <div className="card current-sub stack">
      <div className="row spread">
        <div>
          <span className="muted small">Aktif paketin</span>
          <h2 className="current-sub-title">{subscription.plan.name}</h2>
        </div>
        <span className={subscription.auto_renew ? 'badge success' : 'badge'}>
          {subscription.auto_renew ? 'Otomatik yenilenir' : 'İptal edildi'}
        </span>
      </div>

      <div className="stats">
        <div className="stat">
          <span className="muted small">Kalan kredi</span>
          <strong>{unlimited ? 'Sınırsız' : subscription.remaining_credits}</strong>
        </div>
        <div className="stat">
          <span className="muted small">{subscription.auto_renew ? 'Yenilenme tarihi' : 'Bitiş tarihi'}</span>
          <strong>{formatDate(subscription.expires_at)}</strong>
        </div>
        {subscription.remaining_guest_passes > 0 && (
          <div className="stat">
            <span className="muted small">Misafir hakkı</span>
            <strong>{subscription.remaining_guest_passes}</strong>
          </div>
        )}
      </div>

      {subscription.pending_plan && (
        <p className="alert info">
          {formatDate(subscription.expires_at)} tarihinden itibaren {subscription.pending_plan.name} paketine
          geçilecek.
        </p>
      )}
      {!subscription.auto_renew && (
        <p className="alert info">
          Aboneliğin yenilenmeyecek. Kalan kredilerini {formatDate(subscription.expires_at)} tarihine kadar
          kullanabilirsin.
        </p>
      )}

      {subscription.auto_renew &&
        (confirming ? (
          <div className="confirm-box stack">
            <span>
              Aboneliğini iptal etmek istediğine emin misin? Kalan kredilerin dönem sonuna kadar geçerli kalır.
            </span>
            <div className="row">
              <button type="button" className="button danger" onClick={handleCancel} disabled={cancelling}>
                {cancelling ? 'İptal ediliyor…' : 'Evet, iptal et'}
              </button>
              <button
                type="button"
                className="button secondary"
                onClick={() => setConfirming(false)}
                disabled={cancelling}
              >
                Vazgeç
              </button>
            </div>
          </div>
        ) : (
          <div>
            <button type="button" className="button secondary" onClick={() => setConfirming(true)}>
              İptal Et
            </button>
          </div>
        ))}
    </div>
  )
}
