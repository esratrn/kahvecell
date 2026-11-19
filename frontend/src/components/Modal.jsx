import { useEffect, useRef } from 'react'

// Tarayıcının yerleşik <dialog> öğesi: Esc ile kapanma ve odak yönetimi hazır gelir.
export default function Modal({ title, onClose, children, busy = false }) {
  const dialogRef = useRef(null)

  useEffect(() => {
    const dialog = dialogRef.current
    dialog.showModal()
    return () => dialog.close()
  }, [])

  function handleCancel(event) {
    event.preventDefault()
    if (!busy) {
      onClose()
    }
  }

  function handleBackdropClick(event) {
    if (event.target === dialogRef.current && !busy) {
      onClose()
    }
  }

  return (
    <dialog ref={dialogRef} className="modal" onCancel={handleCancel} onClick={handleBackdropClick}>
      <div className="modal-body stack">
        <div className="row spread">
          <h2>{title}</h2>
          <button type="button" className="toast-close" onClick={onClose} disabled={busy} aria-label="Kapat">
            ×
          </button>
        </div>
        {children}
      </div>
    </dialog>
  )
}
