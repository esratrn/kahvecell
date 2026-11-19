import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { selectIsLoggedIn, useAuthStore } from '../store/authStore'

export default function ProtectedRoute() {
  const isLoggedIn = useAuthStore(selectIsLoggedIn)
  const location = useLocation()

  if (!isLoggedIn) {
    // Girişten sonra kullanıcı gitmek istediği sayfaya geri döner.
    return <Navigate to="/giris" replace state={{ from: location.pathname }} />
  }
  return <Outlet />
}
