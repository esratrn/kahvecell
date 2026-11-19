import axios from 'axios'

import { useAuthStore } from '../store/authStore'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export const client = axios.create({ baseURL, timeout: 15000 })

client.interceptors.request.use((config) => {
  const { accessToken } = useAuthStore.getState()
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

let refreshInFlight = null

async function refreshSession() {
  const { refreshToken, setTokens, clearSession } = useAuthStore.getState()
  if (!refreshToken) {
    clearSession()
    return false
  }
  try {
    // Ayrı axios çağrısı: yenileme isteği kendi interceptor'ına takılıp döngüye girmesin.
    const response = await axios.post(`${baseURL}/auth/refresh`, { refresh_token: refreshToken })
    setTokens(response.data.data)
    return true
  } catch {
    clearSession()
    return false
  }
}

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    const code = error.response?.data?.error?.code

    if (error.response?.status === 401 && code === 'TOKEN_EXPIRED' && !original._retried) {
      original._retried = true
      // Aynı anda süresi dolan birden çok istek tek bir yenileme bekler.
      refreshInFlight ??= refreshSession().finally(() => {
        refreshInFlight = null
      })
      if (await refreshInFlight) {
        return client(original)
      }
    } else if (error.response?.status === 401 && original.headers?.Authorization) {
      useAuthStore.getState().clearSession()
    }
    return Promise.reject(error)
  },
)

export async function request(promise) {
  const response = await promise
  return response.data.data
}

export function getErrorMessage(error) {
  const apiError = error?.response?.data?.error
  if (apiError?.code === 'VALIDATION_ERROR' && apiError.details?.length) {
    return apiError.details.map((detail) => detail.message).join(' ')
  }
  if (apiError?.message) {
    return apiError.message
  }
  if (error?.code === 'ERR_NETWORK') {
    return 'Sunucuya ulaşılamıyor. Backend çalışıyor mu?'
  }
  return 'Beklenmeyen bir hata oluştu.'
}

export function getErrorCode(error) {
  return error?.response?.data?.error?.code ?? null
}
