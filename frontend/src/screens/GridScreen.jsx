import { useEffect, useState } from 'react'

import { api } from '../api'
import { addDays, formatShort, today } from '../dates'
import './GridScreen.css'

// The secondary, laptop-first planning view: a room-by-day matrix answering
// "what does the next couple of weeks look like overall". Deliberately lighter
// than the search screen. On a phone it scrolls horizontally.
export default function GridScreen() {
  const start = today()
  const [from, setFrom] = useState(start)
  const [to, setTo] = useState(addDays(start, 14))
  const [grid, setGrid] = useState(null)
  const [error, setError] = useState(null)

  const validRange = to > from

  useEffect(() => {
    if (!validRange) return
    let cancelled = false
    setError(null)
    api
      .get(`/availability/grid?from=${from}&to=${to}`)
      .then((data) => {
        if (!cancelled) setGrid(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
    return () => {
      cancelled = true
    }
  }, [from, to, validRange])

  function handleFromChange(value) {
    // Auto-correct instead of disabling dates: if the start lands on or after
    // the end, quietly push the end to the day after. The grid query then re-runs
    // with the corrected range.
    setFrom(value)
    if (value >= to) setTo(addDays(value, 1))
  }

  return (
    <main className="grid-screen">
      <form className="range" onSubmit={(event) => event.preventDefault()}>
        <label>
          From
          <input type="date" value={from} onChange={(event) => handleFromChange(event.target.value)} />
        </label>
        <label>
          To
          <input type="date" value={to} onChange={(event) => setTo(event.target.value)} />
        </label>
      </form>

      {!validRange && <p className="hint">The end date must be after the start.</p>}

      {validRange && error && (
        <p className="hint hint--error" role="alert">
          Could not load the planner. {error}
        </p>
      )}

      {validRange && grid && (
        <>
          <p className="grid-caption">
            {formatShort(from)} to {formatShort(to)}
          </p>
          <div className="grid-scroll">
            <table className="grid">
              <thead>
                <tr>
                  <th className="grid__corner">Room</th>
                  {grid.days.map((day) => (
                    <th key={day} className="grid__day" title={formatShort(day)}>
                      {Number(day.split('-')[2])}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {grid.rooms.map((room) => (
                  <tr key={room.room_id}>
                    <th className="grid__room">{room.room_id}</th>
                    {room.days.map((cell) => (
                      <td
                        key={cell.date}
                        className={cell.available ? 'cell cell--free' : 'cell cell--booked'}
                        title={`${room.room_id} · ${formatShort(cell.date)} · ${cell.available ? 'free' : 'booked'}`}
                      />
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="grid-legend">
            <span className="grid-legend__swatch grid-legend__swatch--free" /> Free
            <span className="grid-legend__swatch grid-legend__swatch--booked" /> Booked
          </p>
        </>
      )}
    </main>
  )
}
