const React = require('react')

function Select(props) {
  const {
    options = [],
    value = null,
    onChange,
    isSearchable = true,
    isClearable = false,
    placeholder = '',
    className,
    classNamePrefix = 'react-select',
  } = props

  const [inputValue, setInputValue] = React.useState(value ? value.label || value.value : '')
  const [isOpen, setIsOpen] = React.useState(false)
  const [focusedIndex, setFocusedIndex] = React.useState(-1)
  const containerRef = React.useRef(null)

  React.useEffect(() => {
    if (value) {
      setInputValue(value.label || value.value)
      return
    }
    setInputValue('')
  }, [value])

  React.useEffect(() => {
    function handleClick(event) {
      if (!containerRef.current || containerRef.current.contains(event.target)) {
        return
      }
      setIsOpen(false)
      setFocusedIndex(-1)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const filteredOptions = React.useMemo(() => {
    if (!isSearchable) {
      return options
    }
    if (!inputValue) {
      return options
    }
    const query = inputValue.toLowerCase()
    return options.filter(option => {
      const label = (option.label || option.value || '').toLowerCase()
      const valueText = (option.value || '').toLowerCase()
      return label.includes(query) || valueText.includes(query)
    })
  }, [inputValue, isSearchable, options])

  function handleSelect(option) {
    if (onChange) {
      onChange(option)
    }
    setIsOpen(false)
    setFocusedIndex(-1)
  }

  function handleInputChange(event) {
    const next = event.target.value
    setInputValue(next)
    setIsOpen(true)
    setFocusedIndex(0)
    if (!isSearchable) {
      event.preventDefault()
    }
  }

  function handleKeyDown(event) {
    if (!filteredOptions.length) return
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setIsOpen(true)
      setFocusedIndex(prev => (prev + 1) % filteredOptions.length)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setIsOpen(true)
      setFocusedIndex(prev => (prev - 1 + filteredOptions.length) % filteredOptions.length)
    } else if (event.key === 'Enter') {
      if (focusedIndex >= 0 && filteredOptions[focusedIndex]) {
        event.preventDefault()
        handleSelect(filteredOptions[focusedIndex])
      }
    } else if (event.key === 'Escape') {
      setIsOpen(false)
      setFocusedIndex(-1)
    }
  }

  const controlClassName = [
    `${classNamePrefix}__control`,
    isOpen ? `${classNamePrefix}__control--is-focused` : '',
  ].filter(Boolean).join(' ')

  return React.createElement(
    'div',
    { className, ref: containerRef },
    React.createElement(
      'div',
      { className: controlClassName },
      React.createElement(
        'div',
        { className: `${classNamePrefix}__value-container` },
        React.createElement('input', {
          className: `${classNamePrefix}__input`,
          value: inputValue,
          onChange: handleInputChange,
          onFocus: () => setIsOpen(true),
          onKeyDown: handleKeyDown,
          placeholder,
          readOnly: !isSearchable,
          'aria-autocomplete': 'list',
        }),
      ),
      isClearable && value ? React.createElement(
        'button',
        {
          type: 'button',
          className: `${classNamePrefix}__clear-indicator`,
          onMouseDown: event => event.preventDefault(),
          onClick: () => {
            if (onChange) onChange(null)
            setInputValue('')
            setFocusedIndex(-1)
          },
          'aria-label': 'Clear selected timezone',
        },
        '×',
      ) : null,
      React.createElement(
        'span',
        { className: `${classNamePrefix}__dropdown-indicator`, 'aria-hidden': true },
        '▾',
      ),
    ),
    isOpen && filteredOptions.length ? React.createElement(
      'div',
      { className: `${classNamePrefix}__menu` },
      React.createElement(
        'div',
        { className: `${classNamePrefix}__menu-list` },
        filteredOptions.map((option, index) => React.createElement(
          'div',
          {
            key: option.value,
            className: [
              `${classNamePrefix}__option`,
              index === focusedIndex ? `${classNamePrefix}__option--is-focused` : '',
            ].filter(Boolean).join(' '),
            onMouseDown: event => event.preventDefault(),
            onClick: () => handleSelect(option),
            role: 'option',
            'aria-selected': value ? value.value === option.value : false,
          },
          option.label,
        )),
      ),
    ) : null,
  )
}

module.exports = Select
module.exports.default = Select
