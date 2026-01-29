"use client"

import { useMemo } from 'react'
import Select from 'react-select'
import { getTimeZoneNames } from '../lib/timezones'

type TimezoneOption = {
  value: string
  label: string
}

type TimezoneSelectProps = {
  value: string | null
  onChange: (tzString: string | null) => void
  className?: string
}

export default function TimezoneSelect({ value, onChange, className }: TimezoneSelectProps) {
  const options = useMemo(() => {
    const unique = Array.from(new Set(getTimeZoneNames()))
    return unique.map(timeZone => ({ value: timeZone, label: timeZone }))
  }, [])

  const selectedOption = useMemo(
    () => options.find(option => option.value === value) ?? null,
    [options, value],
  )

  return (
    <Select
      className={className}
      classNamePrefix="timezoneSelect"
      options={options}
      value={selectedOption}
      isSearchable
      isClearable
      placeholder="Select timezone…"
      onChange={option => onChange(option ? option.value : null)}
    />
  )
}
