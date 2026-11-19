import { useToastStore } from '../store/toastStore'

export default function Toaster() {
  const toasts = useToastStore((state) => state.toasts)
  const dismiss = useToastStore((state) => state.dismiss)

  return (
    <div className="toaster" aria-live="polite">
      {toasts.map((item) => (
        <div key={item.id} className={`toast ${item.type}`} role={item.type === 'error' ? 'alert' : 'status'}>
          <span aria-hidden="true">{item.type === 'success' ? '✅' : '⚠️'}</span>
          <span className="toast-message">{item.message}</span>
          <button type="button" className="toast-close" onClick={() => dismiss(item.id)} aria-label="Kapat">
            ×
          </button>
        </div>
      ))}
    </div>
  )
}
