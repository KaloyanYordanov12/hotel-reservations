import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../api'
import { formatShort } from '../dates'
import './ReservationsScreen.css'

const FILTERS = [
  { key: 'all', label: 'All', query: '' },
  { key: 'owes', label: 'Owes deposit', query: '?deposit_paid=false' },
]

// Money is compared as a string, never parsed to a float. "Owes" means the
// deposit is zero; anything else has been paid. Same discipline as the backend.
function hasDeposit(value) {
  return !/^0*(\.0+)?$/.test(String(value).trim())
}

export default function ReservationsScreen() {
  const [filter, setFilter] = useState('all')
  const [reservations, setReservations] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    const query = FILTERS.find((option) => option.key === filter).query
    let cancelled = false
    setError(null)
    api
      .get(`/reservations${query}`)
      .then((data) => {
        if (!cancelled) setReservations(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
    return () => {
      cancelled = true
    }
  }, [filter])

  return (
    <main className="reservations">
      <div className="filters">
        {FILTERS.map((option) => (
          <button
            key={option.key}
            type="button"
            className={option.key === filter ? 'filter filter--active' : 'filter'}
            onClick={() => setFilter(option.key)}
          >
            {option.label}
          </button>
        ))}
      </div>

      {error && (
        <p className="hint hint--error" role="alert">
          Could not load reservations. {error}
        </p>
      )}

      {reservations && reservations.length === 0 && (
        <p className="empty">
          {filter === 'owes' ? 'Everyone has paid a deposit.' : 'No reservations yet.'}
        </p>
      )}

      {reservations && reservations.length > 0 && (
        <ul className="res-list fade-in" key={filter}>
          {reservations.map((reservation) => {
            const paid = hasDeposit(reservation.deposit_paid)
            return (
              <li key={reservation.id}>
                <Link className="res" to={`/book?id=${reservation.id}`}>
                  <span
                    className={`res__dot ${paid ? 'res__dot--paid' : 'res__dot--owes'}`}
                    aria-hidden="true"
                  />
                  <span className="res__body">
                    <span className="res__name">{reservation.guest_name}</span>
                    <span className="res__meta">
                      Room {reservation.room_id} · {formatShort(reservation.check_in)} to{' '}
                      {formatShort(reservation.check_out)}
                    </span>
                  </span>
                  <span
                    className={`res__deposit ${paid ? 'res__deposit--paid' : 'res__deposit--owes'}`}
                  >
                    {paid ? `€${reservation.deposit_paid} paid` : 'Owes deposit'}
                  </span>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </main>
  )
}
