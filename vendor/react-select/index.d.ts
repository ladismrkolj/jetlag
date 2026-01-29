import * as React from 'react'

export type SingleValue<Option> = Option | null

export type Props<Option> = {
  options: Option[]
  value?: SingleValue<Option>
  onChange?: (option: SingleValue<Option>) => void
  isSearchable?: boolean
  isClearable?: boolean
  placeholder?: string
  className?: string
  classNamePrefix?: string
}

export default function Select<Option extends { value: string; label: string }>(
  props: Props<Option>,
): React.ReactElement
