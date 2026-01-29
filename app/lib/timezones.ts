const FALLBACK_TIMEZONES = [
  'UTC',
  'Europe/Ljubljana',
  'Europe/London',
  'America/New_York',
  'America/Los_Angeles',
  'Asia/Tokyo',
]

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
