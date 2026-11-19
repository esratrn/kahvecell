import { useCallback, useEffect, useState } from 'react'

// Sayfa açılınca isteği atar; yükleniyor / hata / veri durumlarını tek yerde tutar.
export function useRequest(requestFn, deps) {
  const [state, setState] = useState({ data: null, error: null, loading: true })

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(requestFn, deps)

  const load = useCallback(
    async ({ silent = false } = {}) => {
      if (!silent) {
        setState((previous) => ({ ...previous, loading: true, error: null }))
      }
      try {
        const data = await run()
        setState({ data, error: null, loading: false })
        return data
      } catch (error) {
        // Arka planda yenilemede hata olursa ekrandaki son veri korunur.
        setState((previous) => (silent ? previous : { ...previous, error, loading: false }))
        return null
      }
    },
    [run],
  )

  useEffect(() => {
    load()
  }, [load])

  return { ...state, reload: load }
}
