"use client"

import { useMemo } from 'react'
import Select from 'react-select'

type TimezoneOption = { value: string; label: string }

const FALLBACK_TIMEZONES = [
  'UTC',
  'Europe/Ljubljana',
  'Europe/London',
  'America/New_York',
  'America/Los_Angeles',
  'Asia/Tokyo',
]

type TimezoneSelectProps = {
  value: string | null
  onChange: (value: string | null) => void
}

function getTimeZoneOptions(): TimezoneOption[] {
  if (typeof Intl !== 'undefined' && typeof (Intl as any).supportedValuesOf === 'function') {
    try {
      const values = (Intl as any).supportedValuesOf('timeZone') as string[]
      if (Array.isArray(values) && values.length) {
        return values.map(value => ({ value, label: value }))
      }
    } catch {}
  }
  return FALLBACK_TIMEZONES.map(value => ({ value, label: value }))
}

export default function TimezoneSelect({ value, onChange }: TimezoneSelectProps) {
  const options = useMemo(() => getTimeZoneOptions(), [])
  const selected = useMemo(() => options.find(option => option.value === value) ?? null, [options, value])

  return (
    <Select<TimezoneOption, false>
      className="timezoneSelect"
      classNamePrefix="timezoneSelect"
      options={options}
      value={selected}
      isSearchable
      isClearable
      placeholder="Select timezone…"
      onChange={option => onChange(option ? option.value : null)}
    />
  )
}
