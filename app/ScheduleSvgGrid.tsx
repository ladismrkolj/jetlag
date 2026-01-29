"use client"
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import styles from './page.module.css'

type Slot = {
  is_sleep: boolean
  is_light: boolean
  is_dark: boolean
  is_travel: boolean
  is_exercise: boolean
  is_melatonin: boolean
  is_cbtmin: boolean
}

type Day = { date: string, slots: Slot[] }

type ScheduleSvgGridProps = {
  days: Day[]
  originOffset: number
  destOffset: number
}

type SlotSegment = {
  start: number
  end: number
}

const NUM_SLOTS = 48
const DEFAULT_LABEL_W = 140
const MIN_COL_W = 16
const NARROW_BREAKPOINT = 640

function hourLabels(offset: number) {
  return Array.from({ length: 24 }, (_, h) => ((h + offset + 24) % 24))
}

function formatHour(hour: number) {
  return hour.toString().padStart(2, '0')
}

function useResizeObserver<T extends HTMLElement>() {
  const ref = useRef<T | null>(null)
  const [size, setSize] = useState({ width: 0, height: 0 })
  const frameRef = useRef<number | null>(null)
  const latestRef = useRef(size)

  useEffect(() => {
    if (!ref.current) return
    const element = ref.current
    const observer = new ResizeObserver(entries => {
      const entry = entries[0]
      if (!entry) return
      const { width, height } = entry.contentRect
      latestRef.current = { width, height }
      if (frameRef.current != null) return
      frameRef.current = requestAnimationFrame(() => {
        frameRef.current = null
        setSize(prev => {
          if (prev.width === latestRef.current.width && prev.height === latestRef.current.height) return prev
          return { ...latestRef.current }
        })
      })
    })
    observer.observe(element)
    return () => {
      observer.disconnect()
      if (frameRef.current != null) cancelAnimationFrame(frameRef.current)
    }
  }, [])

  return { ref, size }
}

function compressSlots(slots: Slot[], bins: number) {
  const slotsPerBin = NUM_SLOTS / bins
  if (slotsPerBin === 1) return slots
  return Array.from({ length: bins }, (_, bin) => {
    const start = bin * slotsPerBin
    const slice = slots.slice(start, start + slotsPerBin)
    return slice.reduce<Slot>((acc, slot) => ({
      is_sleep: acc.is_sleep || slot.is_sleep,
      is_light: acc.is_light || slot.is_light,
      is_dark: acc.is_dark || slot.is_dark,
      is_travel: acc.is_travel || slot.is_travel,
      is_exercise: acc.is_exercise || slot.is_exercise,
      is_melatonin: acc.is_melatonin || slot.is_melatonin,
      is_cbtmin: acc.is_cbtmin || slot.is_cbtmin,
    }), {
      is_sleep: false,
      is_light: false,
      is_dark: false,
      is_travel: false,
      is_exercise: false,
      is_melatonin: false,
      is_cbtmin: false,
    })
  })
}

function buildSegments(slots: Slot[], predicate: (slot: Slot) => boolean) {
  const segments: SlotSegment[] = []
  let start: number | null = null
  slots.forEach((slot, index) => {
    if (predicate(slot)) {
      if (start === null) start = index
      return
    }
    if (start !== null) {
      segments.push({ start, end: index })
      start = null
    }
  })
  if (start !== null) segments.push({ start, end: slots.length })
  return segments
}

export default function ScheduleSvgGrid({ days, originOffset, destOffset }: ScheduleSvgGridProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null)
  const { ref, size } = useResizeObserver<HTMLDivElement>()
  const [scrollLeft, setScrollLeft] = useState(0)

  const width = size.width
  const bins = width > 0 && width < NARROW_BREAKPOINT ? 24 : 48
  const colW = Math.max(MIN_COL_W, (width - DEFAULT_LABEL_W) / bins || MIN_COL_W)
  const canvasWidth = DEFAULT_LABEL_W + bins * colW
  const binsPerHour = bins / 24
  const showMinorLines = colW >= 10

  const hoursOrigin = useMemo(() => hourLabels(originOffset), [originOffset])
  const hoursDest = useMemo(() => hourLabels(destOffset), [destOffset])
  const hoursUtc = useMemo(() => hourLabels(0), [])
  const showUtc = originOffset !== destOffset

  const compressedDays = useMemo(() => days.map(day => ({
    ...day,
    slots: compressSlots(day.slots, bins),
  })), [days, bins])

  useEffect(() => {
    if (!scrollRef.current) return
    const node = scrollRef.current
    const handleScroll = () => setScrollLeft(node.scrollLeft)
    handleScroll()
    node.addEventListener('scroll', handleScroll, { passive: true })
    return () => node.removeEventListener('scroll', handleScroll)
  }, [])

  const timeBinToX = useCallback((binIndex: number) => {
    return DEFAULT_LABEL_W + binIndex * colW - scrollLeft
  }, [colW, scrollLeft])

  const gridStyle = {
    '--bins': bins,
    '--labelW': `${DEFAULT_LABEL_W}px`,
    '--colW': `${colW}px`,
    width: `${canvasWidth}px`,
  } as React.CSSProperties

  const renderGridLines = (keyPrefix: string) => (
    <>
      {Array.from({ length: bins + 1 }, (_, i) => {
        const isHour = i % binsPerHour === 0
        const hourIndex = isHour ? i / binsPerHour : 0
        const isPrimaryHour = isHour && hourIndex % 2 === 1
        if (!showMinorLines && !isHour) return null
        return (
          <span
            key={`${keyPrefix}-line-${i}`}
            className={`${styles.timelineGridLine} ${
              isHour
                ? isPrimaryHour
                  ? styles.timelineGridLinePrimary
                  : styles.timelineGridLineMajor
                : styles.timelineGridLineMinor
            }`}
            style={{ gridColumn: `${i + 2} / span 1` }}
          />
        )
      })}
    </>
  )

  const renderHeaderRow = (label: string, offset: number, hours: number[], key: string) => (
    <div className={`${styles.timelineRow} ${styles.timelineHeaderRow}`} key={key}>
      <div className={`${styles.timelineLabel} ${styles.timelineHeaderLabel}`}>
        <span className={styles.timelineHeaderTitle}>{label}</span>
        <span className={styles.timelineHeaderOffset}>
          (UTC{offset >= 0 ? '+' : ''}{offset})
        </span>
      </div>
      {hours.map((hour, index) => (
        <span
          key={`${key}-hour-${hour}-${index}`}
          className={styles.timelineHourLabel}
          style={{ gridColumn: `${index * binsPerHour + 2} / span ${binsPerHour}` }}
        >
          {formatHour(hour)}
        </span>
      ))}
    </div>
  )

  return (
    <div className={styles.timelineScroll} ref={node => {
      scrollRef.current = node
      ref.current = node
    }}>
      <div className={styles.timelineCanvas} style={gridStyle}>
        <div className={styles.timelineHeaderGroup}>
          {renderHeaderRow('Origin', originOffset, hoursOrigin, 'origin')}
          {showUtc && renderHeaderRow('UTC', 0, hoursUtc, 'utc')}
        </div>
        <div className={styles.timelineBody}>
          {compressedDays.map(day => {
            const sleepSegments = buildSegments(day.slots, slot => slot.is_sleep)
            const lightSegments = buildSegments(day.slots, slot => slot.is_light)
            const darkSegments = buildSegments(day.slots, slot => slot.is_dark)
            const label = day.date
            return (
              <div className={`${styles.timelineRow} ${styles.timelineDayRow}`} key={day.date}>
                <div className={`${styles.timelineLabel} ${styles.timelineDayLabel}`}>
                  {label}
                </div>
                {renderGridLines(`${day.date}-grid`)}
                {sleepSegments.map((segment, index) => (
                  <span
                    key={`${day.date}-sleep-${index}`}
                    className={`${styles.timelineSegment} ${styles.timelineSleep}`}
                    style={{ gridColumn: `${segment.start + 2} / ${segment.end + 2}` }}
                  />
                ))}
                {lightSegments.map((segment, index) => (
                  <span
                    key={`${day.date}-light-${index}`}
                    className={`${styles.timelineSegment} ${styles.timelineLight}`}
                    style={{ gridColumn: `${segment.start + 2} / ${segment.end + 2}` }}
                  />
                ))}
                {darkSegments.map((segment, index) => (
                  <span
                    key={`${day.date}-dark-${index}`}
                    className={`${styles.timelineSegment} ${styles.timelineDark}`}
                    style={{ gridColumn: `${segment.start + 2} / ${segment.end + 2}` }}
                  />
                ))}
                {day.slots.map((slot, index) => {
                  if (!slot.is_travel) return null
                  return (
                    <span
                      key={`${day.date}-travel-${index}`}
                      className={`${styles.timelineMarker} ${styles.markerTravel}`}
                      style={{ gridColumn: `${index + 2} / span 1` }}
                    >
                      t
                    </span>
                  )
                })}
                {day.slots.map((slot, index) => {
                  if (!slot.is_exercise) return null
                  return (
                    <span
                      key={`${day.date}-exercise-${index}`}
                      className={`${styles.timelineMarker} ${styles.markerExercise}`}
                      style={{ gridColumn: `${index + 2} / span 1` }}
                    />
                  )
                })}
                {day.slots.map((slot, index) => {
                  if (!slot.is_melatonin) return null
                  return (
                    <span
                      key={`${day.date}-melatonin-${index}`}
                      className={`${styles.timelineMarker} ${styles.markerMelatonin}`}
                      style={{ gridColumn: `${index + 2} / span 1` }}
                    >
                      M
                    </span>
                  )
                })}
                {day.slots.map((slot, index) => {
                  if (!slot.is_cbtmin) return null
                  return (
                    <span
                      key={`${day.date}-cbtmin-${index}`}
                      className={`${styles.timelineMarker} ${styles.markerCbtmin}`}
                      style={{ gridColumn: `${index + 2} / span 1` }}
                    />
                  )
                })}
              </div>
            )
          })}
        </div>
        <div className={styles.timelineFooterGroup}>
          {renderHeaderRow('Destination', destOffset, hoursDest, 'dest')}
        </div>
      </div>
      <div className={styles.timelineOverlay} aria-hidden="true">
        <div className={styles.timelineOverlayAnchor} style={{ left: timeBinToX(0) }} />
      </div>
    </div>
  )
}
