import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api, setUnauthorizedHandler } from '../api'
import { AuthContext } from './authContext'

// authed: null while we are still checking the cookie, then true or false.
export function AuthProvider({ children }) {
  const [authed, setAuthed] = useState(null)
  const navigate = useNavigate()

  // Any protected call that comes back 401 means the cookie is gone or expired.
  // Send her to login. She logs in once and the 180 day cookie keeps her in, so
  // this is rare, but it must be handled, not crash.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setAuthed(false)
      navigate('/login')
    })
    return () => setUnauthorizedHandler(null)
  }, [navigate])

  // On load, probe whether an existing cookie is still valid by making one
  // protected call. A 200 means she is already in (the common case, one login
  // months ago); a 401 routes her to login via the handler above.
  useEffect(() => {
    let cancelled = false
    api
      .get('/reservations')
      .then(() => {
        if (!cancelled) setAuthed(true)
      })
      .catch(() => {
        if (!cancelled) setAuthed(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (password) => {
    await api.login(password) // throws ApiError on 401 (wrong) or 429 (rate limit)
    setAuthed(true)
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.logout()
    } finally {
      setAuthed(false)
      navigate('/login')
    }
  }, [navigate])

  return (
    <AuthContext.Provider value={{ authed, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
