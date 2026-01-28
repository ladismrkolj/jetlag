"use client"
import { useEffect, useMemo, useRef, useState } from 'react'
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

const NUM_SLOTS = 48

const COLORS = {
  background: '#ffffff',
  grid: '#e5e7eb',
  gridMajor: '#d4d4d8',
  sleep: '#9ca3af',
  light: '#fef08a',
  dark: '#000000',
  travel: '#cbd5e1',
  exercise: '#22c55e',
  marker: '#ef4444',
  label: '#111827',
  labelMuted: '#374151',
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function hourLabels(offset: number) {
  return Array.from({ length: 24 }, (_, h) => ((h + offset + 24) % 24))
}

function formatHour(hour: number) {
  return hour.toString().padStart(2, '0')
}

function baseFill(slot: Slot) {
  if (slot.is_sleep) return COLORS.sleep
  return COLORS.background
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

export default function ScheduleSvgGrid({ days, originOffset, destOffset }: ScheduleSvgGridProps) {
  const { ref, size } = useResizeObserver<HTMLDivElement>()
  const hoursOrigin = useMemo(() => hourLabels(originOffset), [originOffset])
  const hoursDest = useMemo(() => hourLabels(destOffset), [destOffset])

  const numDays = days.length
  const width = size.width
  const height = size.height

  const leftLabelW = clamp(width * 0.18, 80, 140)
  const minCellW = 16
  const minGridW = NUM_SLOTS * minCellW
  const svgWidth = Math.max(width, leftLabelW + minGridW)
  const topHeaderH = clamp(height * 0.12, 30, 60)
  const bottomHeaderH = clamp(height * 0.1, 26, 50)
  const gridW = Math.max(0, svgWidth - leftLabelW)
  const gridH = Math.max(0, height - topHeaderH - bottomHeaderH)
  const cellW = gridW / NUM_SLOTS
  const cellH = numDays ? gridH / numDays : 0

  const showMinorLines = cellW >= 10
  const shortDayLabels = cellH < 18 || leftLabelW < 95

  const headerFont = clamp(cellH * 0.6, 9, 12)
  const labelFont = clamp(cellH * 0.6, 10, 12)
  const timeFont = clamp(cellH * 0.6, 9, 11)

  const dotRadius = clamp(Math.min(cellW, cellH) * 0.18, 2, 4)
  const badgeFont = clamp(Math.min(cellW, cellH) * 0.55, 7, 10)
  const badgePadding = clamp(Math.min(cellW, cellH) * 0.12, 1, 2)

  return (
    <div className={styles.svgGridContainer} ref={ref}>
      <svg className={styles.svgGrid} role="img" aria-label="Schedule grid" width={svgWidth} height={height}>
        <rect x={0} y={0} width={svgWidth} height={height} fill={COLORS.background} />
        {gridW > 0 && gridH > 0 && numDays > 0 && (
          <>
            {days.map((day, dayIndex) => (
              <g key={day.date}>
                {day.slots.map((slot, slotIndex) => {
                  const x = leftLabelW + slotIndex * cellW
                  const y = topHeaderH + dayIndex * cellH
                  const fill = baseFill(slot)
                  return (
                    <g key={`${day.date}:${slotIndex}`}>
                      <rect x={x} y={y} width={cellW} height={cellH} fill={fill} />
                      {slot.is_travel && (
                        <rect x={x} y={y} width={cellW} height={cellH} fill={COLORS.travel} />
                      )}
                      {slot.is_light && (
                        <rect x={x} y={y} width={cellW} height={cellH} fill={COLORS.light} />
                      )}
                      {slot.is_dark && (
                        <rect x={x} y={y} width={cellW} height={cellH} fill={COLORS.dark} />
                      )}
                      {slot.is_exercise && (
                        <rect
                          x={x + 0.5}
                          y={y + 0.5}
                          width={Math.max(0, cellW - 1)}
                          height={Math.max(0, cellH - 1)}
                          fill="none"
                          stroke={COLORS.exercise}
                          strokeWidth={1.4}
                        />
                      )}
                      {slot.is_cbtmin && (
                        <circle
                          cx={x + cellW - dotRadius - 2}
                          cy={y + dotRadius + 2}
                          r={dotRadius}
                          fill={COLORS.marker}
                        />
                      )}
                      {slot.is_travel && (
                        <g>
                          <rect
                            x={x + cellW - (badgeFont + badgePadding * 2) - 2}
                            y={y + cellH - badgeFont - badgePadding * 2 - 2}
                            width={badgeFont + badgePadding * 2}
                            height={badgeFont + badgePadding}
                            rx={2}
                            fill="#ffffffcc"
                            stroke="#9ca3af"
                            strokeWidth={0.8}
                          />
                          <text
                            x={x + cellW - (badgeFont + badgePadding * 2) - 2 + badgePadding}
                            y={y + cellH - badgePadding - 2}
                            fontSize={badgeFont}
                            fill="#111827"
                            fontWeight={700}
                          >
                            t
                          </text>
                        </g>
                      )}
                      {slot.is_melatonin && (
                        <g>
                          <rect
                            x={x + 2}
                            y={y + cellH - badgeFont - badgePadding * 2 - 2}
                            width={badgeFont + badgePadding * 2}
                            height={badgeFont + badgePadding}
                            rx={2}
                            fill="#ffffffcc"
                            stroke={COLORS.marker}
                            strokeWidth={0.8}
                          />
                          <text
                            x={x + 2 + badgePadding}
                            y={y + cellH - badgePadding - 2}
                            fontSize={badgeFont}
                            fill="#b91c1c"
                            fontWeight={700}
                          >
                            M
                          </text>
                        </g>
                      )}
                    </g>
                  )
                })}
              </g>
            ))}

            <rect
              x={leftLabelW}
              y={topHeaderH}
              width={gridW}
              height={gridH}
              fill="none"
              stroke={COLORS.gridMajor}
              strokeWidth={1}
            />

            {Array.from({ length: numDays + 1 }, (_, i) => {
              const y = topHeaderH + i * cellH
              return (
                <line
                  key={`h-${i}`}
                  x1={leftLabelW}
                  x2={leftLabelW + gridW}
                  y1={y}
                  y2={y}
                  stroke={COLORS.grid}
                  strokeWidth={1}
                />
              )
            })}

            {Array.from({ length: NUM_SLOTS + 1 }, (_, i) => {
              const x = leftLabelW + i * cellW
              const isHour = i % 2 === 0
              if (!showMinorLines && !isHour) return null
              return (
                <line
                  key={`v-${i}`}
                  x1={x}
                  x2={x}
                  y1={topHeaderH}
                  y2={topHeaderH + gridH}
                  stroke={isHour ? COLORS.gridMajor : COLORS.grid}
                  strokeWidth={isHour ? 1.4 : 1}
                />
              )
            })}

            {days.map((day, dayIndex) => {
              const label = shortDayLabels ? day.date.slice(5) : day.date
              const y = topHeaderH + dayIndex * cellH + cellH / 2
              return (
                <text
                  key={`day-${day.date}`}
                  x={8}
                  y={y}
                  fontSize={labelFont}
                  fill={COLORS.labelMuted}
                  dominantBaseline="middle"
                >
                  {label}
                </text>
              )
            })}

            <text
              x={8}
              y={topHeaderH / 2}
              fontSize={headerFont}
              fill={COLORS.label}
              dominantBaseline="middle"
              fontWeight={600}
            >
              Origin (UTC{originOffset >= 0 ? '+' : ''}{originOffset})
            </text>

            {hoursOrigin.map((h, idx) => {
              const x = leftLabelW + idx * 2 * cellW + cellW
              return (
                <text
                  key={`origin-hour-${idx}`}
                  x={x}
                  y={topHeaderH / 2}
                  fontSize={timeFont}
                  fill={COLORS.labelMuted}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontWeight={600}
                >
                  {formatHour(h)}
                </text>
              )
            })}

            <text
              x={8}
              y={topHeaderH + gridH + bottomHeaderH / 2}
              fontSize={headerFont}
              fill={COLORS.label}
              dominantBaseline="middle"
              fontWeight={600}
            >
              Destination (UTC{destOffset >= 0 ? '+' : ''}{destOffset})
            </text>

            {hoursDest.map((h, idx) => {
              const x = leftLabelW + idx * 2 * cellW + cellW
              return (
                <text
                  key={`dest-hour-${idx}`}
                  x={x}
                  y={topHeaderH + gridH + bottomHeaderH / 2}
                  fontSize={timeFont}
                  fill={COLORS.labelMuted}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontWeight={600}
                >
                  {formatHour(h)}
                </text>
              )
            })}
          </>
        )}
      </svg>
    </div>
  )
}
