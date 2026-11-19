import { create } from 'zustand'

const TOAST_DURATION_MS = 5000
let nextId = 1

export const useToastStore = create((set) => ({
  toasts: [],

  show: (type, message) => {
    const id = nextId++
    set((state) => ({ toasts: [...state.toasts, { id, type, message }] }))
    setTimeout(() => {
      set((state) => ({ toasts: state.toasts.filter((toast) => toast.id !== id) }))
    }, TOAST_DURATION_MS)
  },

  dismiss: (id) => set((state) => ({ toasts: state.toasts.filter((toast) => toast.id !== id) })),
}))

export const toast = {
  success: (message) => useToastStore.getState().show('success', message),
  error: (message) => useToastStore.getState().show('error', message),
}
