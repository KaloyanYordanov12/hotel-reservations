import { useAuth } from '../auth/authContext'

// Placeholder landing for the protected area. Step 3 replaces this with the
// date-range search screen. It exists now so the auth gate has somewhere to land
// and so logout can be exercised end to end.
export default function Home() {
  const { logout } = useAuth()

  return (
    <main>
      <h1>Hotel Reservations</h1>
      <p>You are logged in. The search screen arrives in Step 3.</p>
      <button type="button" onClick={logout}>
        Log out
      </button>
    </main>
  )
}
