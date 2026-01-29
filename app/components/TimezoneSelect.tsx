"use client"

import { useMemo } from 'react'
import Select from 'react-select'
import { buildTimezoneOptions } from '../lib/timezones'

type TimezoneSelectProps = {
  value: string | null
  onChange: (tzString: string | null) => void
  referenceDate?: Date | null
  className?: string
}

export default function TimezoneSelect({ value, onChange, referenceDate, className }: TimezoneSelectProps) {
  const options = useMemo(() => buildTimezoneOptions(referenceDate), [referenceDate])

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
