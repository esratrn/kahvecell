import { useState } from 'react'

import { getErrorMessage } from '../api/client'
import { changePlan, getMySubscription, listMyPayments, listPlans } from '../api/subscriptions'
import CurrentSubscription from '../components/subscription/CurrentSubscription'
import PlanCard from '../components/subscription/PlanCard'
import PlanChangeModal from '../components/subscription/PlanChangeModal'
import PurchaseModal from '../components/subscription/PurchaseModal'
import { formatDateTime } from '../lib/format'
import { useRequest } from '../lib/useRequest'
import { useAuthStore } from '../store/authStore'
import { toast } from '../store/toastStore'

const PURPOSE_LABELS = {
  NEW_SUBSCRIPTION: 'Yeni abonelik',
  UPGRADE: 'Paket yükseltme',
  RENEWAL: 'Aylık yenileme',
}

function planAction(plan, subscription, { openModal, undoDowngrade }) {
  if (!subscription) {
    return { label: 'Satın Al', onClick: () => openModal('purchase', plan) }
  }
  const current = subscription.plan
  if (plan.code === current.code) {
    if (subscription.pending_plan) {
      return { label: 'Bu pakette kal', onClick: undoDowngrade, secondary: true, note: 'Paket düşürmeyi geri alır.' }
    }
    return { label: 'Mevcut paketin', disabled: true, secondary: true }
  }
  if (subscription.pending_plan?.code === plan.code) {
    return { label: 'Dönem sonunda geçilecek', disabled: true, secondary: true }
  }
  if (plan.price_kurus > current.price_kurus) {
    return { label: 'Yükselt', onClick: () => openModal('change', plan) }
  }
  if (!subscription.auto_renew) {
    return { label: 'Düşür', disabled: true, secondary: true, note: 'İptal edilen abonelik düşürülemez.' }
  }
  return { label: 'Düşür', onClick: () => openModal('change', plan), secondary: true }
}

export default function SubscriptionPage() {
  const user = useAuthStore((state) => state.user)
  const plansRequest = useRequest(listPlans, [])
  const subscriptionRequest = useRequest(getMySubscription, [])
  const paymentsRequest = useRequest(listMyPayments, [])
  const [modal, setModal] = useState(null)

  const subscription = subscriptionRequest.data

  function refresh() {
    subscriptionRequest.reload({ silent: true })
    paymentsRequest.reload({ silent: true })
  }

  function handleModalDone() {
    setModal(null)
    refresh()
  }

  async function undoDowngrade() {
    try {
      const result = await changePlan(subscription.plan.code)
      toast.success(result.message)
      refresh()
    } catch (err) {
      toast.error(getErrorMessage(err))
    }
  }

  const openModal = (type, plan) => setModal({ type, plan })

  function closeModal() {
    setModal(null)
    // Başarısız ödeme de geçmişe yazılır.
    paymentsRequest.reload({ silent: true })
  }

  if (plansRequest.loading || subscriptionRequest.loading) {
    return <p className="muted">Yükleniyor…</p>
  }
  const loadError = plansRequest.error ?? subscriptionRequest.error
  if (loadError) {
    return <p className="alert error">{getErrorMessage(loadError)}</p>
  }

  const payments = paymentsRequest.data ?? []

  return (
    <section className="stack">
      <h1>Abonelik</h1>

      <CurrentSubscription subscription={subscription} onChanged={refresh} />

      <h2>{subscription ? 'Paketini değiştir' : 'Paketler'}</h2>
      <div className="plan-grid">
        {plansRequest.data.map((plan) => (
          <PlanCard
            key={plan.code}
            plan={plan}
            highlight={subscription?.plan.code === plan.code}
            action={planAction(plan, subscription, { openModal, undoDowngrade })}
          />
        ))}
      </div>

      {payments.length > 0 && (
        <details className="card payments">
          <summary>Ödeme geçmişi ({payments.length})</summary>
          <ul className="list">
            {payments.map((payment) => (
              <li key={payment.transaction_id} className="list-item">
                <span>
                  {PURPOSE_LABELS[payment.purpose]} · {payment.plan_code}
                  <span className="muted small block">
                    {formatDateTime(payment.created_at)} · {payment.transaction_id}
                  </span>
                </span>
                <span className="row">
                  <strong>{payment.amount_display}</strong>
                  <span className={payment.status === 'SUCCESS' ? 'badge success' : 'badge danger'}>
                    {payment.status === 'SUCCESS' ? 'Başarılı' : 'Başarısız'}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}

      {modal?.type === 'purchase' && (
        <PurchaseModal
          plan={modal.plan}
          holderName={user?.full_name}
          onClose={closeModal}
          onPurchased={handleModalDone}
        />
      )}
      {modal?.type === 'change' && subscription && (
        <PlanChangeModal
          subscription={subscription}
          plan={modal.plan}
          holderName={user?.full_name}
          onClose={closeModal}
          onChanged={handleModalDone}
        />
      )}
    </section>
  )
}
