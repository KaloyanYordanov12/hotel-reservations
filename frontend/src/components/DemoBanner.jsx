import { useEffect, useState } from 'react'

import { api } from '../api'
import { strings as t } from '../strings'
import './DemoBanner.css'

// Shown only on the public demo deployment. It asks the backend once whether
// this is the demo (GET /api/demo-status, a public endpoint) and renders nothing
// unless it is, so the real app looks exactly as it does now. It must be honest:
// this is seeded sample data that resets on a schedule.
export default function DemoBanner() {
  const [demo, setDemo] = useState(false)

  useEffect(() => {
    let cancelled = false
    api
      .get('/demo-status')
      .then((data) => {
        if (!cancelled) setDemo(Boolean(data && data.demo))
      })
      .catch(() => {
        // If the check fails, stay silent rather than guess. Never show a demo
        // banner over what might be the real app.
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (!demo) return null
  return (
    <div className="demo-banner" role="note">
      {t.demo.banner}
    </div>
  )
}
