import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useAuthStore = create(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,

      setSession: ({ access_token, refresh_token, user }) =>
        set({ accessToken: access_token, refreshToken: refresh_token, user }),

      setTokens: ({ access_token, refresh_token }) =>
        set({ accessToken: access_token, refreshToken: refresh_token }),

      setUser: (user) => set({ user }),

      clearSession: () => set({ accessToken: null, refreshToken: null, user: null }),
    }),
    // Sayfa yenilense de oturum korunsun diye tarayıcıda saklanır.
    { name: 'kahvecell-auth' },
  ),
)

export const selectIsLoggedIn = (state) => Boolean(state.accessToken)
