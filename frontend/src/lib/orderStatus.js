export const ORDER_STATUS = {
  PENDING: {
    label: 'Bekliyor',
    tone: 'pending',
    icon: '⏳',
    hint: 'Siparişin dükkâna iletildi, onay bekleniyor.',
  },
  ACCEPTED: {
    label: 'Kabul Edildi',
    tone: 'accepted',
    icon: '👍',
    hint: 'Dükkân siparişini aldı, birazdan hazırlamaya başlayacak.',
  },
  PREPARING: {
    label: 'Hazırlanıyor',
    tone: 'preparing',
    icon: '☕',
    hint: 'Kahven şu an hazırlanıyor.',
  },
  READY: {
    label: 'Hazır',
    tone: 'ready',
    icon: '🔔',
    hint: 'Kahven hazır! Dükkânda bu QR kodu göster.',
  },
  COMPLETED: {
    label: 'Teslim Edildi',
    tone: 'completed',
    icon: '✅',
    hint: 'Siparişin teslim edildi.',
  },
  CANCELLED: {
    label: 'İptal Edildi',
    tone: 'cancelled',
    icon: '✖',
    hint: 'Bu sipariş iptal edildi; kahve kredin iade edildi.',
  },
}

export const STATUS_FLOW = ['PENDING', 'ACCEPTED', 'PREPARING', 'READY', 'COMPLETED']

export const FINISHED_STATUSES = ['COMPLETED', 'CANCELLED']
