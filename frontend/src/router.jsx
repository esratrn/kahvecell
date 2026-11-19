import { createBrowserRouter } from 'react-router-dom'

import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import HistoryPage from './pages/HistoryPage'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import NotFoundPage from './pages/NotFoundPage'
import OrderPage from './pages/OrderPage'
import QrPage from './pages/QrPage'
import RegisterPage from './pages/RegisterPage'
import ShopDetailPage from './pages/ShopDetailPage'
import SubscriptionPage from './pages/SubscriptionPage'

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: '/', element: <HomePage /> },
      { path: '/giris', element: <LoginPage /> },
      { path: '/dukkan/:shopId', element: <ShopDetailPage /> },
      {
        // Bu sayfalar yalnızca giriş yapmış kullanıcıya açık.
        element: <ProtectedRoute />,
        children: [
          { path: '/kayit', element: <RegisterPage /> },
          { path: '/dukkan/:shopId/siparis', element: <OrderPage /> },
          { path: '/siparis/:orderId', element: <QrPage /> },
          { path: '/gecmis', element: <HistoryPage /> },
          { path: '/abonelik', element: <SubscriptionPage /> },
        ],
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
