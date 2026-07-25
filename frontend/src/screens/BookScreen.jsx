import { Link, useSearchParams } from 'react-router-dom'

import { formatShort } from '../dates'

// Placeholder for Step 5's booking form (create and edit in one component). It
// exists now to prove both entry points carry their context in the URL, so a
// refresh keeps it and the Step 5 form opens already filled in, never blank:
//   - from search: room + dates (a new booking)
//   - from the reservations list: id (editing an existing one)
export default function BookScreen() {
  const [params] = useSearchParams()
  const id = params.get('id')
  const room = params.get('room')
  const checkIn = params.get('check_in')
  const checkOut = params.get('check_out')

  return (
    <main className="book">
      <h1>{id ? 'Edit booking' : 'New booking'}</h1>
      {id ? (
        <p className="hint">
          Editing reservation <strong>{id}</strong>.
        </p>
      ) : room ? (
        <p className="hint">
          Room <strong>{room}</strong>
          {checkIn && checkOut && (
            <>
              , {formatShort(checkIn)} to {formatShort(checkOut)}
            </>
          )}
          .
        </p>
      ) : (
        <p className="hint">No room selected. Start from availability.</p>
      )}
      <p className="hint">
        The booking form arrives in Step 5. It will open already filled with this
        context.
      </p>
      <Link to={id ? '/reservations' : '/'}>Back</Link>
    </main>
  )
}
