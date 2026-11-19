import { useEffect, useState } from 'react'

// Kullanıcı yazmayı bırakınca değeri günceller; her tuşta sunucuya istek atılmaz.
export function useDebouncedValue(value, delayMs = 300) {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(timer)
  }, [value, delayMs])

  return debounced
}
