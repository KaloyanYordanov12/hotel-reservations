import { Navigate, Outlet } from 'react-router-dom'

import { strings as t } from '../strings'
import { useAuth } from './authContext'

// Gate for the protected routes. While the cookie check is in flight we show a
// tiny placeholder; once known, either render the route or bounce to login.
export function RequireAuth() {
  const { authed } = useAuth()

  if (authed === null) return <p>{t.common.loading}</p>
  if (!authed) return <Navigate to="/login" replace />
  return <Outlet />
}
