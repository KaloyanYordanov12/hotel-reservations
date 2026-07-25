import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../api'
import { useAuth } from '../auth/authContext'
import { addDays, formatShort, today } from '../dates'
import './SearchScreen.css'

// The primary screen: she is on the phone with a guest asking "anything free
// from the 20th to the 24th?" and needs the answer in seconds. Two dates,
// prefilled to tonight, and a list of what is free. Free rooms are tappable and
// carry the room and dates into the booking form.
export default function SearchScreen() {
  const start = today()
  const [checkIn, setCheckIn] = useState(start)
  const [checkOut, setCheckOut] = useState(addDays(start, 1))
  const [rooms, setRooms] = useState(null)
  const [error, setError] = useState(null)
  const { logout } = useAuth()

  const validRange = checkOut > checkIn

  useEffect(() => {
    if (!validRange) return
    let cancelled = false
    setError(null)
    api
      .get(`/availability?check_in=${checkIn}&check_out=${checkOut}`)
      .then((data) => {
        if (!cancelled) setRooms(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
    return () => {
      cancelled = true
    }
  }, [checkIn, checkOut, validRange])

  // The backend already decides free vs booked (same-day turnover reads as free);
  // we only display what it returns, never recompute it.
  const free = rooms ? rooms.filter((room) => room.available) : []
  const booked = rooms ? rooms.filter((room) => !room.available) : []

  return (
    <main className="search">
      <header className="search__top">
        <h1>Availability</h1>
        <button type="button" className="ghost" onClick={logout}>
          Log out
        </button>
      </header>

      <form className="range" onSubmit={(event) => event.preventDefault()}>
        <label>
          Check in
          <input
            type="date"
            value={checkIn}
            max={checkOut}
            onChange={(event) => setCheckIn(event.target.value)}
          />
        </label>
        <label>
          Check out
          <input
            type="date"
            value={checkOut}
            min={checkIn}
            onChange={(event) => setCheckOut(event.target.value)}
          />
        </label>
      </form>

      {!validRange && <p className="hint">Check-out must be after check-in.</p>}

      {validRange && error && (
        <p className="hint hint--error" role="alert">
          Could not load availability. {error}
        </p>
      )}

      {validRange && rooms && (
        <div className="results fade-in" key={`${checkIn}_${checkOut}`}>
          <section>
            <h2>Free · {free.length}</h2>
            {free.length === 0 && <p className="empty">No rooms free for these dates.</p>}
            <ul className="rooms">
              {free.map((room) => (
                <li key={room.room_id}>
                  <Link
                    className="room room--free"
                    to={`/book?room=${encodeURIComponent(room.room_id)}&check_in=${checkIn}&check_out=${checkOut}`}
                  >
                    <span className="room__id">{room.room_id}</span>
                    <span className="room__body">
                      <span className="room__meta">
                        {room.type} · sleeps {room.standard_occupancy}
                      </span>
                    </span>
                    <span className="room__tag room__tag--free">Free</span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>

          {booked.length > 0 && (
            <section>
              <h2>Booked · {booked.length}</h2>
              <ul className="rooms">
                {booked.map((room) => (
                  <li key={room.room_id}>
                    <div className="room room--booked">
                      <span className="room__id">{room.room_id}</span>
                      <span className="room__body">
                        <span className="room__meta">
                          {room.type} · sleeps {room.standard_occupancy}
                        </span>
                        {room.reservation && (
                          <span className="room__guest">
                            {room.reservation.guest_name}, {formatShort(room.reservation.check_in)} to{' '}
                            {formatShort(room.reservation.check_out)}
                          </span>
                        )}
                      </span>
                      <span className="room__tag room__tag--booked">Booked</span>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </main>
  )
}
