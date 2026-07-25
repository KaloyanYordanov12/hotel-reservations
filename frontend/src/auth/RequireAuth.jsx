import { Navigate, Outlet } from 'react-router-dom'

import { useAuth } from './authContext'

// Gate for the protected routes. While the cookie check is in flight we show a
// tiny placeholder; once known, either render the route or bounce to login.
export function RequireAuth() {
  const { authed } = useAuth()

  if (authed === null) return <p>Loading...</p>
  if (!authed) return <Navigate to="/login" replace />
  return <Outlet />
}
