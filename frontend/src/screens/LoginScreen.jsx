import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../auth/authContext'

export default function LoginScreen() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(password)
      navigate('/')
    } catch (err) {
      // 429 (rate limited) is distinct from a plain wrong password, so she is
      // not left retrying a password that would be rejected regardless.
      if (err.status === 429) {
        setError('Too many attempts. Wait a minute and try again.')
      } else if (err.status === 401) {
        setError('Wrong password.')
      } else {
        setError('Could not log in. Is the backend running?')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main>
      <h1>Hotel Reservations</h1>
      <form onSubmit={handleSubmit}>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoFocus
          />
        </label>
        <button type="submit" disabled={submitting}>
          {submitting ? 'Logging in...' : 'Log in'}
        </button>
        {error && <p role="alert">{error}</p>}
      </form>
    </main>
  )
}
