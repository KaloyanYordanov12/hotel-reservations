import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { api } from '../api'
import { addDays, formatShort, today } from '../dates'
import { strings as t } from '../strings'
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
    init().catch(() => {
      if (!cancelled) {
        setLoading(false)
        setError(t.booking.loadError)
      }
    })
    return () => {
      cancelled = true
    }
    // Only re-run if the edited id changes.
  }, [id]) // eslint-disable-line react-hooks/exhaustive-deps

  function showSubmitError(err) {
    if (err.status === 409) {
      // Build the clash message from the structured detail, not the backend's
      // English text, so the UI stays fully Bulgarian.
      const detail = err.body && err.body.detail
      if (detail && detail.conflict) {
        setError(
          t.booking.conflict(
            detail.room_id,
            detail.conflict.guest_name,
            formatShort(detail.conflict.check_in),
            formatShort(detail.conflict.check_out),
          ),
        )
      } else {
        setError(t.booking.conflictGeneric)
      }
    } else if (err.status === 422) {
      // Map the offending field from the pydantic error to a Bulgarian message.
      const detail = err.body && err.body.detail
      const field =
        Array.isArray(detail) && detail[0] && Array.isArray(detail[0].loc)
          ? detail[0].loc[detail[0].loc.length - 1]
          : null
      if (field === 'num_guests') setError(t.booking.guestsMin)
      else if (field === 'deposit_paid') setError(t.booking.depositNegative)
      else setError(t.booking.validationGeneric)
    } else {
      setError(t.booking.saveError)
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
    if (!guestName.trim()) missing.push(t.booking.fields.guestName)
    if (!guestPhone.trim()) missing.push(t.booking.fields.phone)
    if (!roomId) missing.push(t.booking.fields.room)
    if (!checkIn) missing.push(t.booking.fields.checkIn)
    if (!checkOut) missing.push(t.booking.fields.checkOut)
    if (!numGuests) missing.push(t.booking.fields.guests)
    if (missing.length) {
      setError(t.booking.fillIn(missing.join(', ')))
      return
    }
    if (checkOut <= checkIn) {
      setError(t.booking.invalidRange)
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
    } catch {
      setError(t.booking.deleteError)
    }
  }

  if (loading) {
    return (
      <main className="book">
        <p>{t.common.loading}</p>
      </main>
    )
  }

  const roomOptions = rooms || (roomId ? [{ id: roomId, type: '' }] : [])

  return (
    <main className="book">
      <h1>{isEdit ? t.booking.titleEdit : t.booking.titleNew}</h1>

      <form className="form" onSubmit={handleSubmit}>
        <label className="field">
          {t.booking.guestName}
          <input value={guestName} onChange={(e) => setGuestName(e.target.value)} autoFocus={!isEdit} />
        </label>

        <label className="field">
          {t.booking.phone}
          <input type="tel" value={guestPhone} onChange={(e) => setGuestPhone(e.target.value)} />
        </label>

        <label className="field">
          {t.booking.room}
          <select value={roomId} onChange={(e) => setRoomId(e.target.value)}>
            {!roomId && <option value="">{t.booking.pickRoom}</option>}
            {roomOptions.map((room) => (
              <option key={room.id} value={room.id}>
                {room.id}
                {room.type ? ` (${t.roomTypes[room.type] || room.type})` : ''}
              </option>
            ))}
          </select>
        </label>

        <div className="field-row">
          <label className="field">
            {t.booking.checkIn}
            <input type="date" value={checkIn} onChange={(e) => handleCheckInChange(e.target.value)} />
          </label>
          <label className="field">
            {t.booking.checkOut}
            <input type="date" value={checkOut} onChange={(e) => setCheckOut(e.target.value)} />
          </label>
        </div>

        <div className="field-row">
          <label className="field">
            {t.booking.guests}
            <input
              type="number"
              min="1"
              inputMode="numeric"
              value={numGuests}
              onChange={(e) => setNumGuests(e.target.value)}
            />
          </label>
          <label className="field">
            {t.booking.deposit}
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
          {t.booking.parking}
        </label>

        <label className="field">
          {t.booking.note}
          <textarea rows="3" value={note} onChange={(e) => setNote(e.target.value)} />
        </label>

        {error && (
          <p className="hint hint--error" role="alert">
            {error}
          </p>
        )}

        <div className="actions">
          <button type="submit" disabled={submitting}>
            {submitting ? t.booking.submitting : isEdit ? t.booking.submitEdit : t.booking.submitNew}
          </button>
          <button
            type="button"
            className="ghost"
            onClick={() => navigate(isEdit ? '/reservations' : '/')}
          >
            {t.booking.cancel}
          </button>
        </div>
      </form>

      {isEdit && (
        <div className="danger">
          {confirmingDelete ? (
            <>
              <span>{t.booking.deleteQuestion}</span>
              <button type="button" className="danger__yes" onClick={handleDelete}>
                {t.booking.deleteYes}
              </button>
              <button type="button" className="ghost" onClick={() => setConfirmingDelete(false)}>
                {t.booking.cancel}
              </button>
            </>
          ) : (
            <button type="button" className="ghost danger__trigger" onClick={() => setConfirmingDelete(true)}>
              {t.booking.deleteTrigger}
            </button>
          )}
        </div>
      )}
    </main>
  )
}
