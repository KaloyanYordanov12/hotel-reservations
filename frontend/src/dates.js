// Local-time date helpers. The whole system is DATE only, no timezones, so we
// format and step dates in local components and never touch toISOString (which
// is UTC and would shift the day).

export function toISODate(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function today() {
  return toISODate(new Date())
}

export function addDays(isoDate, days) {
  const [year, month, day] = isoDate.split('-').map(Number)
  const date = new Date(year, month - 1, day)
  date.setDate(date.getDate() + days)
  return toISODate(date)
}

// "2026-08-10" -> "10.08". Bulgarian day-first numeric format.
export function formatShort(isoDate) {
  const [, month, day] = isoDate.split('-').map(Number)
  return `${String(day).padStart(2, '0')}.${String(month).padStart(2, '0')}`
}
