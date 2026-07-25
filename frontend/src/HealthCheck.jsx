import { useEffect, useState } from 'react'

// The smallest thing that proves the pipe: the dev server, the proxy, and the
// backend all talk. It hits /health (which is not under /api and is unprotected)
// through the Vite proxy. This is a Step 1 scaffolding check; later steps build
// the real screens.
export default function HealthCheck() {
  const [status, setStatus] = useState('checking...')

  useEffect(() => {
    let cancelled = false
    fetch('/health')
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        return response.json()
      })
      .then((data) => {
        if (!cancelled) setStatus(data.status)
      })
      .catch((error) => {
        if (!cancelled) setStatus(`unreachable (${error.message})`)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <p>
      Backend health: <strong>{status}</strong>
    </p>
  )
}
