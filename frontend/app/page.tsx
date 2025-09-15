"use client"
import { useMemo, useState } from 'react'
import styles from './page.module.css'

type TzOffset = number // in hours, e.g. -5 for New York winter

export default function Page() {
  const [originOffset, setOriginOffset] = useState<TzOffset>(-5)
  const [destOffset, setDestOffset] = useState<TzOffset>(1)
  const [originSleepStart, setOriginSleepStart] = useState('23:00')
  const [originSleepEnd, setOriginSleepEnd] = useState('07:00')
  const [destSleepStart, setDestSleepStart] = useState('23:00')
  const [destSleepEnd, setDestSleepEnd] = useState('07:00')
  const [travelStart, setTravelStart] = useState('2025-09-10T18:00')
  const [travelEnd, setTravelEnd] = useState('2025-09-11T08:00')
  const [useMelatonin, setUseMelatonin] = useState(true)
  const [useLightDark, setUseLightDark] = useState(true)
  const [useExercise, setUseExercise] = useState(false)
  const [preDays, setPreDays] = useState(2)
  const [events, setEvents] = useState<any[] | null>(null)
  const [debugSlots, setDebugSlots] = useState<any[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          originOffset,
          destOffset,
          originSleepStart,
          originSleepEnd,
          destSleepStart,
          destSleepEnd,
          travelStart,
          travelEnd,
          useMelatonin,
          useLightDark,
          useExercise,
          preDays,
        })
      })
      if (!res.ok) throw new Error(`API error: ${res.status}`)
      const data = await res.json()
      setEvents(data.events)
      setDebugSlots(null)
    } catch (err: any) {
      setError(err.message || 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const onLoadSample = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/debug-slots.json')
      if (!res.ok) throw new Error(`Fetch error: ${res.status}`)
      const data = await res.json()
      setDebugSlots(data)
      setEvents(null)
    } catch (err:any) {
      setError(err.message || 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className={styles.main}>
      <h1 className={styles.title}>Jet Lag Planner</h1>
      <form className={styles.form} onSubmit={onSubmit}>
        <div className={styles.row}>
          <label>Origin offset (h)</label>
          <input type="number" step="0.5" value={originOffset} onChange={e => setOriginOffset(parseFloat(e.target.value))} />
          <label>Destination offset (h)</label>
          <input type="number" step="0.5" value={destOffset} onChange={e => setDestOffset(parseFloat(e.target.value))} />
          <label>Precondition days</label>
          <input type="number" min={0} value={preDays} onChange={e => setPreDays(parseInt(e.target.value || '0', 10))} />
        </div>
        <div className={styles.row}>
          <label>Origin sleep</label>
          <input type="time" value={originSleepStart} onChange={e => setOriginSleepStart(e.target.value)} />
          <span>→</span>
          <input type="time" value={originSleepEnd} onChange={e => setOriginSleepEnd(e.target.value)} />
          <label>Destination sleep</label>
          <input type="time" value={destSleepStart} onChange={e => setDestSleepStart(e.target.value)} />
          <span>→</span>
          <input type="time" value={destSleepEnd} onChange={e => setDestSleepEnd(e.target.value)} />
        </div>
        <div className={styles.row}>
          <label>Travel start (origin local)</label>
          <input type="datetime-local" value={travelStart} onChange={e => setTravelStart(e.target.value)} />
          <label>Travel end (destination local)</label>
          <input type="datetime-local" value={travelEnd} onChange={e => setTravelEnd(e.target.value)} />
        </div>
        <div className={styles.row}>
          <label><input type="checkbox" checked={useMelatonin} onChange={e => setUseMelatonin(e.target.checked)} /> Melatonin</label>
          <label><input type="checkbox" checked={useLightDark} onChange={e => setUseLightDark(e.target.checked)} /> Light/Dark</label>
          <label><input type="checkbox" checked={useExercise} onChange={e => setUseExercise(e.target.checked)} /> Exercise</label>
        </div>
        <div className={styles.actions}>
          <button type="submit" disabled={loading}>{loading ? 'Calculating…' : 'Calculate'}</button>
          <button type="button" onClick={onLoadSample} disabled={loading}>Load sample slots</button>
        </div>
      </form>

      {error && <p className={styles.error}>{error}</p>}

      {events && <TimetableGrid events={events} />}
      {debugSlots && <DebugSlotsGrid slots={debugSlots} />}
    </main>
  )
}

function TimetableGrid({ events }: { events: any[] }) {
  // Group events by UTC date for display; 48 columns (30-minute slots)
  const days = useMemo(() => groupEventsByUTCDate(events), [events])
  const hours = Array.from({ length: 24 }, (_, i) => i)

  return (
    <div className={styles.gridWrap}>
      <div className={styles.legend}>
        <span className={styles.legendBox + ' ' + styles.sleep}>Sleep</span>
        <span className={styles.legendBox + ' ' + styles.light}>Light</span>
        <span className={styles.legendBox + ' ' + styles.dark}>Dark</span>
        <span className={styles.legendBox + ' ' + styles.exercise}>Exercise</span>
        <span className={styles.legendBox + ' ' + styles.melatonin}>Melatonin</span>
        <span className={styles.legendBox + ' ' + styles.cbtmin}>CBTmin</span>
        <span className={styles.legendBox + ' ' + styles.travel}>Travel</span>
      </div>
      <div className={styles.grid}>
        <div className={styles.headerCell}></div>
        {hours.map(h => (
          <div key={h} className={styles.headerHour} style={{ gridColumn: 'span 2' }}>
            {`${h.toString().padStart(2,'0')}:00`}
          </div>
        ))}
        {days.map((d) => (
          <Row key={d.date} day={d} />
        ))}
      </div>
    </div>
  )
}

function DebugSlotsGrid({ slots }: { slots: any[] }) {
  // Group provided slots by UTC date
  const days = useMemo(() => {
    const byDate = new Map<string, any[]>()
    for (const s of slots) {
      const d = String(s.start).slice(0,10)
      if (!byDate.has(d)) byDate.set(d, [])
      byDate.get(d)!.push(s)
    }
    return Array.from(byDate.entries()).map(([date, list]) => {
      // Sort by start
      list.sort((a,b) => String(a.start).localeCompare(String(b.start)))
      return { date, slots: list }
    })
  }, [slots])

  const hours = Array.from({ length: 24 }, (_, i) => i)
  return (
    <div className={styles.gridWrap}>
      <div className={styles.legend}>
        <span className={styles.legendBox + ' ' + styles.sleep}>Sleep</span>
        <span className={styles.legendBox + ' ' + styles.light}>Light</span>
        <span className={styles.legendBox + ' ' + styles.dark}>Dark</span>
        <span className={styles.legendBox + ' ' + styles.exercise}>Exercise</span>
        <span className={styles.legendBox + ' ' + styles.melatonin}>Melatonin</span>
        <span className={styles.legendBox + ' ' + styles.travel}>Travel</span>
      </div>
      <div className={styles.grid}>
        <div className={styles.headerCell}></div>
        {hours.map(h => (
          <div key={h} className={styles.headerHour} style={{ gridColumn: 'span 2' }}>
            {`${h.toString().padStart(2,'0')}:00`}
          </div>
        ))}
        {days.map((d) => (
          <>
            <div key={d.date+':label'} className={styles.rowLabel}>{d.date}</div>
            {d.slots.map((slot, i) => (
              <Cell key={d.date+':'+i} slot={slot} />
            ))}
          </>
        ))}
      </div>
    </div>
  )
}

function Row({ day }: { day: ReturnType<typeof groupEventsByUTCDate>[number] }) {
  return (
    <>
      <div className={styles.rowLabel}>{day.date}</div>
      {day.slots.map((slot, i) => (
        <Cell key={i} slot={slot} />
      ))}
    </>
  )
}

function Cell({ slot }: { slot: ReturnType<typeof groupEventsByUTCDate>[number]['slots'][number] }) {
  const classes = [styles.cell]
  if (slot.is_sleep) classes.push(styles.sleep)
  if (slot.is_light) classes.push(styles.light)
  if (slot.is_dark) classes.push(styles.dark)
  if (slot.is_travel) classes.push(styles.travel)
  if (slot.is_exercise) classes.push(styles.exercise)
  // melatonin as a marker dot
  return (
    <div className={classes.join(' ')}>
      {slot.is_melatonin && <span className={styles.dot} />}
      {slot.is_cbtmin && <span className={styles.cbtDot} />}
    </div>
  )
}

function groupEventsByUTCDate(events: any[]) {
  // Build 30-minute slots for each UTC day spanned by events
  const parse = (s: string | null) => (s ? new Date(s) : null)
  if (!events.length) return [] as any[]
  const starts = events.map(e => parse(e.start)).filter(Boolean) as Date[]
  const ends = events.map(e => parse(e.end)).filter(Boolean) as Date[]
  const minStart = new Date(Math.min(...starts.map(d => d.getTime())))
  const maxEnd = ends.length ? new Date(Math.max(...ends.map(d => d.getTime()))) : new Date(Math.max(...starts.map(d => d.getTime())))
  // Normalize to UTC midnights
  const startDay = new Date(Date.UTC(minStart.getUTCFullYear(), minStart.getUTCMonth(), minStart.getUTCDate()))
  const endDay = new Date(Date.UTC(maxEnd.getUTCFullYear(), maxEnd.getUTCMonth(), maxEnd.getUTCDate()))
  // inclusive end day
  const days: { date: string, slots: any[] }[] = []
  for (let d = new Date(startDay); d <= endDay; d = new Date(d.getTime() + 24*3600*1000)) {
    const dateStr = d.toISOString().slice(0,10)
    const slots = [] as any[]
    for (let i = 0; i < 48; i++) {
      const slotStart = new Date(d.getTime() + i*30*60*1000)
      const slotEnd = new Date(d.getTime() + (i+1)*30*60*1000)
      // aggregate flags if any event overlaps
      const flags = { is_sleep:false, is_light:false, is_dark:false, is_travel:false, is_exercise:false, is_melatonin:false, is_cbtmin:false }
      for (const e of events) {
        const es = parse(e.start)
        const ee = parse(e.end)
        let occurs = false
        if (ee == null && es) {
          occurs = es >= slotStart && es < slotEnd
        } else if (es && ee) {
          occurs = es < slotEnd && ee > slotStart
        }
        if (occurs) {
          for (const k of Object.keys(flags) as (keyof typeof flags)[]) {
            if (e[k]) flags[k] = true
          }
        }
      }
      slots.push({ ...flags, start: slotStart.toISOString(), end: slotEnd.toISOString() })
    }
    days.push({ date: dateStr, slots })
  }
  return days
}
