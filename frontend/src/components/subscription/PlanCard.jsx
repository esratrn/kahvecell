const POPULAR_PLAN = 'PREMIUM'

function planFeatures(plan) {
  const features = [
    plan.is_unlimited ? 'Sınırsız kahve' : `Ayda ${plan.monthly_credits} kahve`,
    plan.valid_at,
  ]
  if (plan.guest_passes > 0) {
    features.push(`${plan.guest_passes} misafir hakkı`)
  }
  if (plan.has_priority) {
    features.push('Sipariş önceliği')
  }
  return features
}

// action: { label, onClick, disabled, note } | null
export default function PlanCard({ plan, action, highlight }) {
  const isPopular = plan.code === POPULAR_PLAN

  return (
    <article className={`plan-card ${isPopular ? 'popular' : ''} ${highlight ? 'current' : ''}`}>
      {isPopular && <span className="plan-ribbon">En çok tercih edilen</span>}
      <h3 className="plan-name">{plan.name}</h3>
      <p className="plan-price">
        <strong>{plan.price_display}</strong>
        <span className="muted small"> / ay</span>
      </p>
      <ul className="plan-features">
        {planFeatures(plan).map((feature) => (
          <li key={feature}>{feature}</li>
        ))}
      </ul>
      {action && (
        <div className="stack plan-action">
          <button
            type="button"
            className={action.secondary ? 'button secondary' : 'button'}
            onClick={action.onClick}
            disabled={action.disabled}
          >
            {action.label}
          </button>
          {action.note && <span className="muted small center-text">{action.note}</span>}
        </div>
      )}
    </article>
  )
}
