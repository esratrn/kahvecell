import { ORDER_STATUS } from '../lib/orderStatus'

export default function OrderStatusBadge({ status }) {
  const meta = ORDER_STATUS[status]
  return <span className={`badge status-${meta.tone}`}>{meta.label}</span>
}
