import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../api'
import { addDays, formatShort, today } from '../dates'
import { strings as t } from '../strings'
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
        if (!cancelled) setError(err)
      })
    return () => {
      cancelled = true
    }
  }, [checkIn, checkOut, validRange])

  function handleCheckInChange(value) {
    // Auto-correct instead of disabling dates: if check-in lands on or after
    // check-out, quietly push check-out to the day after. The impossible state
    // never forms, and the availability query re-runs with the corrected range.
    setCheckIn(value)
    if (value >= checkOut) setCheckOut(addDays(value, 1))
  }

  // The backend already decides free vs booked (same-day turnover reads as free);
  // we only display what it returns, never recompute it.
  const free = rooms ? rooms.filter((room) => room.available) : []
  const booked = rooms ? rooms.filter((room) => !room.available) : []

  return (
    <main className="search">
      <form className="range" onSubmit={(event) => event.preventDefault()}>
        <label>
          {t.search.checkIn}
          <input
            type="date"
            value={checkIn}
            onChange={(event) => handleCheckInChange(event.target.value)}
          />
        </label>
        <label>
          {t.search.checkOut}
          <input
            type="date"
            value={checkOut}
            onChange={(event) => setCheckOut(event.target.value)}
          />
        </label>
      </form>

      {!validRange && <p className="hint">{t.search.invalidRange}</p>}

      {validRange && error && (
        <p className="hint hint--error" role="alert">
          {t.search.loadError}
        </p>
      )}

      {validRange && rooms && (
        <div className="results fade-in" key={`${checkIn}_${checkOut}`}>
          <section>
            <h2>
              {t.search.freeHeading} · {free.length}
            </h2>
            {free.length === 0 && <p className="empty">{t.search.noneFree}</p>}
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
                        {t.roomTypes[room.type] || room.type} · {t.search.sleeps(room.standard_occupancy)}
                      </span>
                    </span>
                    <span className="room__tag room__tag--free">{t.search.freeTag}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>

          {booked.length > 0 && (
            <section>
              <h2>
                {t.search.bookedHeading} · {booked.length}
              </h2>
              <ul className="rooms">
                {booked.map((room) => (
                  <li key={room.room_id}>
                    <div className="room room--booked">
                      <span className="room__id">{room.room_id}</span>
                      <span className="room__body">
                        <span className="room__meta">
                          {t.roomTypes[room.type] || room.type} · {t.search.sleeps(room.standard_occupancy)}
                        </span>
                        {room.reservation && (
                          <span className="room__guest">
                            {room.reservation.guest_name}, {formatShort(room.reservation.check_in)} {t.common.to}{' '}
                            {formatShort(room.reservation.check_out)}
                          </span>
                        )}
                      </span>
                      <span className="room__tag room__tag--booked">{t.search.bookedTag}</span>
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
