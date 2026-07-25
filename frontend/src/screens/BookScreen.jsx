import { Link, useSearchParams } from 'react-router-dom'

import { formatShort } from '../dates'

// Placeholder for Step 5's booking form. It exists now to prove the design rule
// that booking carries search context: the tapped room and the searched dates
// arrive here in the URL, so a refresh keeps them and the Step 5 form will open
// already filled in rather than blank.
export default function BookScreen() {
  const [params] = useSearchParams()
  const room = params.get('room')
  const checkIn = params.get('check_in')
  const checkOut = params.get('check_out')

  return (
    <main className="book">
      <h1>New booking</h1>
      {room ? (
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
        room and these dates.
      </p>
      <Link to="/">Back to availability</Link>
    </main>
  )
}
