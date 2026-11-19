import { create } from 'zustand'

import { ANKARA_KIZILAY } from '../lib/leaflet'

// status: idle → locating → granted | denied | unavailable
export const useLocationStore = create((set, get) => ({
  coords: ANKARA_KIZILAY,
  status: 'idle',

  requestLocation: () => {
    // Oturum boyunca bir kez sorulur; sayfa değiştikçe izin penceresi tekrar açılmaz.
    if (get().status !== 'idle') {
      return
    }
    if (!('geolocation' in navigator)) {
      set({ status: 'unavailable' })
      return
    }
    set({ status: 'locating' })
    navigator.geolocation.getCurrentPosition(
      (position) =>
        set({ coords: [position.coords.latitude, position.coords.longitude], status: 'granted' }),
      (error) => set({ status: error.code === error.PERMISSION_DENIED ? 'denied' : 'unavailable' }),
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 5 * 60 * 1000 },
    )
  },
}))
