import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { api } from '../api'
import { addDays, today } from '../dates'
import './BookScreen.css'

// One form for both create and edit. It opens already filled from context: from
// a tapped free room (room + dates in the URL) or from the reservations list (an
// id, whose reservation is loaded). Validation is deliberately minimal, per the
// standing rule: required fields present and check-out after check-in, nothing
// else. num_guests has no max, over-occupancy is fine, note is free text. The
// backend is the final judge; a 409 or 422 is shown clearly and stays fixable.
export default function BookScreen() {
  const [params] = useSearchParams()
  const id = params.get('id')
  const isEdit = Boolean(id)
  const navigate = useNavigate()

  const [roomId, setRoomId] = useState(params.get('room') || '')
  const [guestName, setGuestName] = useState('')
  const [guestPhone, setGuestPhone] = useState('')
  const [checkIn, setCheckIn] = useState(params.get('check_in') || today())
  const [checkOut, setCheckOut] = useState(params.get('check_out') || addDays(today(), 1))
  const [numGuests, setNumGuests] = useState('2')
  const [parking, setParking] = useState(false)
  const [deposit, setDeposit] = useState('0') // kept as a string, no float math
  const [note, setNote] = useState('')

  const [rooms, setRooms] = useState(null)
  const [loading, setLoading] = useState(isEdit)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function init() {
      let dates = { ci: checkIn, co: checkOut }
      if (isEdit) {
        const r = await api.get(`/reservations/${id}`)
        if (cancelled) return
        setRoomId(r.room_id)
        setGuestName(r.guest_name)
        setGuestPhone(r.guest_phone)
        setCheckIn(r.check_in)
        setCheckOut(r.check_out)
        setNumGuests(String(r.num_guests))
        setParking(r.parking)
        setDeposit(String(r.deposit_paid))
        setNote(r.note || '')
        setLoading(false)
        dates = { ci: r.check_in, co: r.check_out }
      }
      // The 10 rooms are static; availability is the only endpoint that lists
      // them, so fetch it once (with valid dates) just for the room options.
      if (dates.ci && dates.co && dates.co > dates.ci) {
        const availability = await api.get(
          `/availability?check_in=${dates.ci}&check_out=${dates.co}`,
        )
        if (!cancelled) {
          setRooms(availability.map((room) => ({ id: room.room_id, type: room.type })))
        }
      }
    }
    init().catch((err) => {
      if (!cancelled) {
        setLoading(false)
        setError(err.message)
      }
    })
    return () => {
      cancelled = true
    }
    // Only re-run if the edited id changes.
  }, [id]) // eslint-disable-line react-hooks/exhaustive-deps

  function showSubmitError(err) {
    if (err.status === 409) {
      const detail = err.body && err.body.detail
      setError((detail && detail.message) || 'Those dates clash with another booking.')
    } else if (err.status === 422) {
      const detail = err.body && err.body.detail
      if (Array.isArray(detail) && detail.length) setError(detail[0].msg)
      else setError(typeof detail === 'string' ? detail : 'Please check the fields.')
    } else {
      setError(err.message)
    }
  }

  function handleCheckInChange(value) {
    // Auto-correct instead of disabling dates: if check-in lands on or after
    // check-out, quietly push check-out to the day after, so the impossible
    // state never forms.
    setCheckIn(value)
    if (value >= checkOut) setCheckOut(addDays(value, 1))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)

    const missing = []
    if (!guestName.trim()) missing.push('guest name')
    if (!guestPhone.trim()) missing.push('phone')
    if (!roomId) missing.push('room')
    if (!checkIn) missing.push('check-in')
    if (!checkOut) missing.push('check-out')
    if (!numGuests) missing.push('guests')
    if (missing.length) {
      setError(`Please fill in: ${missing.join(', ')}.`)
      return
    }
    if (checkOut <= checkIn) {
      setError('Check-out must be after check-in.')
      return
    }

    const payload = {
      room_id: roomId,
      guest_name: guestName,
      guest_phone: guestPhone,
      check_in: checkIn,
      check_out: checkOut,
      num_guests: Number(numGuests),
      parking,
      deposit_paid: deposit === '' ? '0' : deposit,
      note: note === '' ? null : note, // free text, never parsed or trimmed
    }

    setSubmitting(true)
    try {
      if (isEdit) await api.patch(`/reservations/${id}`, payload)
      else await api.post('/reservations', payload)
      navigate(isEdit ? '/reservations' : '/')
    } catch (err) {
      showSubmitError(err)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete() {
    setError(null)
    try {
      await api.del(`/reservations/${id}`)
      navigate('/reservations')
    } catch (err) {
      setError(err.message)
    }
  }

  if (loading) {
    return (
      <main className="book">
        <p>Loading...</p>
      </main>
    )
  }

  const roomOptions = rooms || (roomId ? [{ id: roomId, type: '' }] : [])

  return (
    <main className="book">
      <h1>{isEdit ? 'Edit booking' : 'New booking'}</h1>

      <form className="form" onSubmit={handleSubmit}>
        <label className="field">
          Guest name
          <input value={guestName} onChange={(e) => setGuestName(e.target.value)} autoFocus={!isEdit} />
        </label>

        <label className="field">
          Phone
          <input type="tel" value={guestPhone} onChange={(e) => setGuestPhone(e.target.value)} />
        </label>

        <label className="field">
          Room
          <select value={roomId} onChange={(e) => setRoomId(e.target.value)}>
            {!roomId && <option value="">Pick a room</option>}
            {roomOptions.map((room) => (
              <option key={room.id} value={room.id}>
                {room.id}
                {room.type ? ` (${room.type})` : ''}
              </option>
            ))}
          </select>
        </label>

        <div className="field-row">
          <label className="field">
            Check in
            <input type="date" value={checkIn} onChange={(e) => handleCheckInChange(e.target.value)} />
          </label>
          <label className="field">
            Check out
            <input type="date" value={checkOut} onChange={(e) => setCheckOut(e.target.value)} />
          </label>
        </div>

        <div className="field-row">
          <label className="field">
            Guests
            <input
              type="number"
              min="1"
              inputMode="numeric"
              value={numGuests}
              onChange={(e) => setNumGuests(e.target.value)}
            />
          </label>
          <label className="field">
            Deposit (EUR)
            <input
              type="text"
              inputMode="decimal"
              value={deposit}
              onChange={(e) => setDeposit(e.target.value)}
            />
          </label>
        </div>

        <label className="field-check">
          <input type="checkbox" checked={parking} onChange={(e) => setParking(e.target.checked)} />
          Parking
        </label>

        <label className="field">
          Note
          <textarea rows="3" value={note} onChange={(e) => setNote(e.target.value)} />
        </label>

        {error && (
          <p className="hint hint--error" role="alert">
            {error}
          </p>
        )}

        <div className="actions">
          <button type="submit" disabled={submitting}>
            {submitting ? 'Saving...' : isEdit ? 'Save changes' : 'Create booking'}
          </button>
          <button
            type="button"
            className="ghost"
            onClick={() => navigate(isEdit ? '/reservations' : '/')}
          >
            Cancel
          </button>
        </div>
      </form>

      {isEdit && (
        <div className="danger">
          {confirmingDelete ? (
            <>
              <span>Delete this booking?</span>
              <button type="button" className="danger__yes" onClick={handleDelete}>
                Yes, delete
              </button>
              <button type="button" className="ghost" onClick={() => setConfirmingDelete(false)}>
                Cancel
              </button>
            </>
          ) : (
            <button type="button" className="ghost danger__trigger" onClick={() => setConfirmingDelete(true)}>
              Delete booking
            </button>
          )}
        </div>
      )}
    </main>
  )
}
