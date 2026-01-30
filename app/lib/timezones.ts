const FALLBACK_TIMEZONES = [
  'UTC',
  'Europe/Ljubljana',
  'Europe/London',
  'America/New_York',
  'America/Los_Angeles',
  'Asia/Tokyo',
]

export type TimezoneOption = {
  value: string
  label: string
}

export function getTimeZoneNames(): string[] {
  if (typeof Intl !== 'undefined' && typeof (Intl as any).supportedValuesOf === 'function') {
    try {
      const values = (Intl as any).supportedValuesOf('timeZone') as string[]
      if (Array.isArray(values) && values.length) {
        return values
      }
    } catch {}
  }
  return FALLBACK_TIMEZONES
}

export function buildTimezoneOptions(referenceDate?: Date | null): TimezoneOption[] {
  const ref = referenceDate ?? new Date()
  const unique = Array.from(new Set(getTimeZoneNames()))
  return unique.map(timeZone => {
    const offset = getTimeZoneOffsetHours(timeZone, ref)
    return { value: timeZone, label: formatTimeZoneLabel(timeZone, offset) }
  })
}

export function getTimeZoneOffsetHours(timeZone: string, referenceDate?: Date | null): number | null {
  try {
    const date = referenceDate ?? new Date()
    const minutes = getTimeZoneOffsetMinutes(timeZone, date)
    if (!Number.isFinite(minutes)) return null
    return minutes / 60
  } catch {
    return null
  }
}

function getTimeZoneOffsetMinutes(timeZone: string, date: Date): number {
  const dtf = new Intl.DateTimeFormat('en-US', {
    timeZone,
    hour12: false,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
  const parts = dtf.formatToParts(date)
  const map = new Map<string, string>()
  for (const part of parts) {
    map.set(part.type, part.value)
  }
  const year = Number(map.get('year'))
  const month = Number(map.get('month'))
  const day = Number(map.get('day'))
  const hour = Number(map.get('hour'))
  const minute = Number(map.get('minute'))
  const second = Number(map.get('second'))
  const asUTC = Date.UTC(year, month - 1, day, hour, minute, second)
  return (asUTC - date.getTime()) / 60000
}

function formatOffsetForDisplay(offset: number): string {
  const totalMinutes = Math.round(Math.abs(offset) * 60)
  const sign = offset >= 0 ? '+' : '-'
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return `UTC${sign}${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
}

function formatTimeZoneLabel(timeZone: string, offset: number | null): string {
  const readable = timeZone.replace(/_/g, ' ')
  return offset == null ? readable : `${readable} (${formatOffsetForDisplay(offset)})`
}
