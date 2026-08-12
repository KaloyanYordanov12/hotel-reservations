// Thin wrapper over fetch. Every call sends the session cookie (credentials:
// "include"), same-origin. There is nothing for the app to store: the cookie is
// the whole auth mechanism and the browser holds it. Do not put a password or
// token in localStorage.
//
// Errors are surfaced as ApiError with a status, so callers can distinguish
// 401 (not logged in), 409 (booking conflict), 422 (validation), 429 (rate
// limited), and everything else, and show the right message.

export class ApiError extends Error {
  constructor(status, body) {
    super(ApiError.messageFor(status, body))
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }

  static messageFor(status, body) {
    const detail = body && body.detail
    if (typeof detail === 'string') return detail
    if (detail && typeof detail === 'object' && detail.message) return detail.message
    if (status === 0) return 'Network error. Is the backend running?'
    return `Request failed (${status})`
  }
}

// Base URL for the API. Empty by default, so the real app calls the API on its
// own origin (the same FastAPI process serves both). The demo frontend is a
// separate Cloudflare Pages project on a different origin, so its build sets
// VITE_API_URL to the demo backend's URL (e.g. https://reservations-demo...);
// these calls then go cross-origin to that backend, which allows this origin via
// CORS in demo mode. A trailing slash is trimmed so the joined URL stays clean.
const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

// The auth gate registers a handler here so that any protected call returning
// 401 sends her back to login, wherever it happens.
let onUnauthorized = null
export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler
}

async function request(method, path, body) {
  let response
  try {
    response = await fetch(`${API_BASE}/api${path}`, {
      method,
      credentials: 'include',
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, null)
  }

  if (response.status === 204) return null

  let data = null
  const text = await response.text()
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }

  if (!response.ok) {
    // A wrong-password 401 on /login is handled by the login screen itself, so
    // it must not trip the global gate; only protected calls do.
    if (response.status === 401 && path !== '/login' && onUnauthorized) {
      onUnauthorized()
    }
    throw new ApiError(response.status, data)
  }
  return data
}

export const api = {
  get: (path) => request('GET', path),
  post: (path, body) => request('POST', path, body),
  patch: (path, body) => request('PATCH', path, body),
  del: (path) => request('DELETE', path),
  login: (password) => request('POST', '/login', { password }),
  logout: () => request('POST', '/logout'),
}
