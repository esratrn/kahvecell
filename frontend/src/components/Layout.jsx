import { NavLink, Outlet, useNavigate } from 'react-router-dom'

import { logout } from '../api/auth'
import { selectIsLoggedIn, useAuthStore } from '../store/authStore'
import Toaster from './Toaster'

export default function Layout() {
  const isLoggedIn = useAuthStore(selectIsLoggedIn)
  const user = useAuthStore((state) => state.user)
  const navigate = useNavigate()

  async function handleLogout() {
    const { refreshToken, clearSession } = useAuthStore.getState()
    try {
      await logout(refreshToken)
    } catch {
      // Sunucuya ulaşılamasa da kullanıcı bu cihazda çıkış yapmış olmalı.
    }
    clearSession()
    navigate('/giris')
  }

  return (
    <div className="app">
      <header className="header">
        <NavLink to="/" className="brand">
          ☕ KahveCell
        </NavLink>
        <nav className="nav">
          <NavLink to="/" end>
            Dükkânlar
          </NavLink>
          {isLoggedIn && (
            <>
              <NavLink to="/abonelik">Abonelik</NavLink>
              <NavLink to="/gecmis">Geçmiş</NavLink>
            </>
          )}
        </nav>
        <div className="nav-user">
          {isLoggedIn ? (
            <>
              <span className="muted">{user?.full_name ?? user?.phone_number}</span>
              <button type="button" className="button secondary" onClick={handleLogout}>
                Çıkış
              </button>
            </>
          ) : (
            <NavLink to="/giris" className="button">
              Giriş yap
            </NavLink>
          )}
        </div>
      </header>
      <main className="container">
        <Outlet />
      </main>
      <Toaster />
    </div>
  )
}
