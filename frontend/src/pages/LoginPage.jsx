import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

import { requestOtp, verifyOtp } from '../api/auth'
import { getErrorMessage } from '../api/client'
import { selectIsLoggedIn, useAuthStore } from '../store/authStore'

export default function LoginPage() {
  const isLoggedIn = useAuthStore(selectIsLoggedIn)
  const setSession = useAuthStore((state) => state.setSession)
  const navigate = useNavigate()
  const location = useLocation()

  const [step, setStep] = useState('phone')
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [devCode, setDevCode] = useState(null)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  if (isLoggedIn && step === 'phone') {
    return <Navigate to="/" replace />
  }

  async function handleRequestCode(event) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const result = await requestOtp(phone)
      setDevCode(result.dev_otp_code)
      setStep('code')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  async function handleVerify(event) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const session = await verifyOtp(phone, code)
      setSession(session)
      const destination = session.user.is_profile_complete ? location.state?.from ?? '/' : '/kayit'
      navigate(destination, { replace: true })
    } catch (err) {
      setError(getErrorMessage(err))
      setSubmitting(false)
    }
  }

  return (
    <section className="card narrow">
      <h1>Giriş yap</h1>
      <p className="muted">Hesabın yoksa ilk girişte otomatik oluşturulur.</p>

      {step === 'phone' ? (
        <form className="stack" onSubmit={handleRequestCode}>
          <label className="field">
            GSM numarası
            <input
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              placeholder="0555 555 55 55"
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              required
            />
          </label>
          {error && <p className="alert error">{error}</p>}
          <button type="submit" className="button" disabled={submitting}>
            {submitting ? 'Gönderiliyor…' : 'Kod gönder'}
          </button>
        </form>
      ) : (
        <form className="stack" onSubmit={handleVerify}>
          <p>
            <strong>{phone}</strong> numarasına kod gönderildi.
          </p>
          {devCode && <p className="alert info">SMS simülasyonu: kodunuz {devCode}</p>}
          <label className="field">
            Doğrulama kodu
            <input
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="\d{4}"
              maxLength={4}
              placeholder="1234"
              value={code}
              onChange={(event) => setCode(event.target.value.replace(/\D/g, ''))}
              required
              autoFocus
            />
          </label>
          {error && <p className="alert error">{error}</p>}
          <button type="submit" className="button" disabled={submitting || code.length !== 4}>
            {submitting ? 'Doğrulanıyor…' : 'Giriş yap'}
          </button>
          <button
            type="button"
            className="button link"
            onClick={() => {
              setStep('phone')
              setCode('')
              setError(null)
            }}
          >
            Numarayı değiştir
          </button>
        </form>
      )}
    </section>
  )
}
