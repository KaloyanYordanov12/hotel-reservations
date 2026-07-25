import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../auth/authContext'
import { strings as t } from '../strings'

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
        setError(t.login.tooManyAttempts)
      } else if (err.status === 401) {
        setError(t.login.wrongPassword)
      } else {
        setError(t.login.failed)
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main>
      <h1>{t.login.title}</h1>
      <form onSubmit={handleSubmit}>
        <label>
          {t.login.passwordLabel}
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoFocus
          />
        </label>
        <button type="submit" disabled={submitting}>
          {submitting ? t.login.submitting : t.login.submit}
        </button>
        {error && <p role="alert">{error}</p>}
      </form>
    </main>
  )
}
