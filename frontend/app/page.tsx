"use client"
import { useEffect, useMemo, useState } from 'react'
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
  const [reportOpen, setReportOpen] = useState(false)
  const [reportComment, setReportComment] = useState('')
  const [reportEmail, setReportEmail] = useState('')
  const [reportSending, setReportSending] = useState(false)
  const [reportMessage, setReportMessage] = useState<string | null>(null)
  const [includeScreenshot, setIncludeScreenshot] = useState(true)
  const [betaOpen, setBetaOpen] = useState(false)
  const [quickOpen, setQuickOpen] = useState(false)
  const [quickRating, setQuickRating] = useState<string | null>(null)
  const [quickName, setQuickName] = useState('')
  const [quickComment, setQuickComment] = useState('')
  const [quickEmail, setQuickEmail] = useState('')
  const [quickSending, setQuickSending] = useState(false)
  const [quickMessage, setQuickMessage] = useState<string | null>(null)
  const [nameSuggestion, setNameSuggestion] = useState('')
  const [betaEmail, setBetaEmail] = useState('')

  useEffect(() => {
    // For beta: show on every reload for now
    setBetaOpen(true)
  }, [])

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

      {events && <TimetableGrid events={events} originOffset={originOffset} destOffset={destOffset} />}
      {debugSlots && <DebugSlotsGrid slots={debugSlots} originOffset={originOffset} destOffset={destOffset} />}

      {(events || debugSlots) && (
        <div className={styles.emojiBand}>
          <button className={styles.emojiButton} aria-label="Love it" onClick={() => { setQuickRating('heart'); setQuickOpen(true); setQuickMessage(null) }}>❤️</button>
          <button className={styles.emojiButton} aria-label="Great" onClick={() => { setQuickRating('party'); setQuickOpen(true); setQuickMessage(null) }}>🎉</button>
          <button className={styles.emojiButton} aria-label="Not good" onClick={() => { setQuickRating('down'); setQuickOpen(true); setQuickMessage(null) }}>👎</button>
        </div>
      )}

      <div className={styles.footer}>
        <button className={styles.reportBtn} type="button" onClick={() => { setReportOpen(true); setReportMessage(null) }}>
          Report a problem or suggestion
        </button>
      </div>

      {reportOpen && (
        <div className={styles.modalBackdrop} data-html2canvas-ignore onClick={() => !reportSending && setReportOpen(false)}>
          <div className={styles.modal} data-html2canvas-ignore onClick={e => e.stopPropagation()}>
            <h3>Send Feedback</h3>
            <p className={styles.muted}>Optional: describe the issue or suggestion. We’ll include anonymous debug info.</p>
            <textarea placeholder="Your message (optional)" value={reportComment} onChange={e => setReportComment(e.target.value)} />
            <div className={styles.row}>
              <label><input type="checkbox" checked={includeScreenshot} onChange={e => setIncludeScreenshot(e.target.checked)} /> Include page screenshot</label>
            </div>
            <div className={styles.row}>
              <input
                placeholder="Email for updates (optional)"
                value={reportEmail}
                onChange={e => setReportEmail(e.target.value)}
                style={{flex:1,padding:'8px',border:'1px solid #e5e7eb',borderRadius:'8px'}}
              />
            </div>
            <div className={styles.row}>
              <button className={styles.reportBtn} type="button" disabled={reportSending} onClick={async () => {
                setReportSending(true)
                setReportMessage(null)
                try {
                  let screenshot: string | null = null
                  if (includeScreenshot && typeof window !== 'undefined') {
                    try {
                      const html2canvas = (await import('html2canvas')).default
                      const canvas = await html2canvas(document.body, { logging: false, useCORS: true, scale: 1 })
                      screenshot = canvas.toDataURL('image/jpeg', 0.85)
                    } catch (e) {
                      console.warn('screenshot capture failed', e)
                    }
                  }
                  const payload = {
                    comment: reportComment,
                    inputs: {
                      originOffset, destOffset, originSleepStart, originSleepEnd, destSleepStart, destSleepEnd,
                      travelStart, travelEnd, useMelatonin, useLightDark, useExercise, preDays
                    },
                    data: events ?? debugSlots ?? null,
                    userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown',
                    url: typeof location !== 'undefined' ? location.href : 'unknown',
                    screenshot,
                    email: (reportEmail || '').trim() || null,
                  }
                  // attach full rasterized slots
                  try {
                    let slotsPayload: any[] = []
                    if (Array.isArray(debugSlots) && debugSlots.length) {
                      slotsPayload = debugSlots
                    } else if (Array.isArray(events) && events.length) {
                      const days = groupEventsByUTCDate(events)
                      slotsPayload = ([] as any[]).concat(...days.map(d => d.slots))
                    }
                    ;(payload as any).slots = slotsPayload
                  } catch {}
                  const res = await fetch('/api/report', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
                  const body = await res.json().catch(() => ({}))
                  if (!res.ok) throw new Error(body.error || `HTTP ${res.status}`)
                  setReportMessage('Thanks! Your feedback was sent.')
                  setReportComment('')
                } catch (e) {
                  const msg = (e && typeof e === 'object' && 'message' in e) ? (e as any).message : 'unknown error'
                  setReportMessage(`Could not send: ${msg}`)
                } finally {
                  setReportSending(false)
                }
              }}>
                {reportSending ? 'Sending…' : ((reportEmail || '').trim() ? 'Send & Subscribe' : 'Send')}
              </button>
              <button className={styles.reportBtn} type="button" onClick={() => setReportOpen(false)} disabled={reportSending}>Close</button>
            </div>
            {reportMessage && <p className={styles.muted}>{reportMessage}</p>}
          </div>
        </div>
      )}

      {betaOpen && (
        <div className={styles.modalBackdrop} data-html2canvas-ignore onClick={() => setBetaOpen(false)}>
          <div className={styles.modal} data-html2canvas-ignore onClick={e => e.stopPropagation()}>
            <h3>Beta Notice</h3>
            <p className={styles.muted}>This tool is in beta. Results are experimental and should not be used for medical decisions.</p>
            <p className={styles.muted}>After you try the tool, you can share feedback or suggest a name using the feedback button.</p>
            <div className={styles.row}>
              <input placeholder="Email for updates (optional)" value={betaEmail} onChange={e=>setBetaEmail(e.target.value)} style={{flex:1,padding:'8px',border:'1px solid #e5e7eb',borderRadius:'8px'}} />
            </div>
            <div className={styles.row}>
              <button className={styles.reportBtn} type="button" onClick={async ()=>{ const email=(betaEmail||'').trim(); if(email){ try{ await fetch('/api/report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'subscribe',email,source:'beta_modal',url: typeof location!=='undefined'?location.href:'unknown'})}) }catch{} } setBetaOpen(false) }}>{(betaEmail||'').trim() ? 'I understand & Subscribe' : 'I understand'}</button>
            </div>
          </div>
        </div>
      )}

      {quickOpen && (
        <div className={styles.modalBackdrop} data-html2canvas-ignore onClick={() => !quickSending && setQuickOpen(false)}>
          <div className={styles.modal} data-html2canvas-ignore onClick={e => e.stopPropagation()}>
            <h3>Quick Feedback</h3>
            <p className={styles.muted}>How did it go? Your selected reaction: {quickRating === 'heart' ? '❤️ Love it' : quickRating === 'party' ? '🎉 Great' : '👎 Not good'}</p>
            <textarea placeholder="What worked? What didn’t? (optional)" value={quickComment} onChange={e => setQuickComment(e.target.value)} />
            <div className={styles.row}>
              <input placeholder="Suggest a name for the site (optional)" value={quickName} onChange={e=>setQuickName(e.target.value)} style={{flex:1,padding:'8px',border:'1px solid #e5e7eb',borderRadius:'8px'}} />
            </div>
            <div className={styles.row}>
              <input placeholder="Email for updates (optional)" value={quickEmail} onChange={e=>setQuickEmail(e.target.value)} style={{flex:1,padding:'8px',border:'1px solid #e5e7eb',borderRadius:'8px'}} />
            </div>
            <div className={styles.row}>
              <button className={styles.reportBtn} type="button" disabled={quickSending} onClick={async ()=>{
                setQuickSending(true); setQuickMessage(null)
                try{
                  const payload:any={
                    type:'quick_feedback',
                    rating:quickRating,
                    comment:quickComment || null,
                    nameSuggestion:quickName || null,
                    email: (quickEmail || '').trim() || null,
                    inputs:{ originOffset, destOffset, preDays },
                    url: typeof location!=='undefined'?location.href:'unknown',
                  }
                  const res=await fetch('/api/report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
                  const body=await res.json().catch(()=>({}))
                  if(!res.ok) throw new Error(body.error||`HTTP ${res.status}`)
                  setQuickMessage('Thanks for the feedback!')
                  setQuickName(''); setQuickComment(''); setQuickEmail('')
                }catch(e:any){ setQuickMessage(e?.message||'Failed to send') }
                finally{ setQuickSending(false) }
              }}>{quickSending?'Sending…':((quickEmail||'').trim()?'Send & Subscribe':'Send')}</button>
              <button className={styles.reportBtn} type="button" onClick={()=>setQuickOpen(false)} disabled={quickSending}>Close</button>
            </div>
            {quickMessage && <p className={styles.muted}>{quickMessage}</p>}
          </div>
        </div>
      )}
    </main>
  )
}

function hourLabels(offset: number) {
  return Array.from({ length: 24 }, (_, h) => ((h + offset + 24) % 24))
}

function TimetableGrid({ events, originOffset, destOffset }: { events: any[], originOffset: number, destOffset: number }) {
  // Group events by UTC date for display; 48 columns (30-minute slots)
  const days = useMemo(() => groupEventsByUTCDate(events), [events])
  const hoursUTC = Array.from({ length: 24 }, (_, i) => i)
  const hoursOrigin = hourLabels(originOffset)
  const hoursDest = hourLabels(destOffset)

  const lastDay0Date = useMemo(() => {
    const dates: string[] = []
    for (const e of events) {
      if (e.day_index === 0 && typeof e.start === 'string') {
        dates.push(String(e.start).slice(0,10))
      }
    }
    return dates.length ? dates.sort().at(-1)! : null
  }, [events])

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
      {/* Top legend: Origin local time */}
      <div className={styles.legendRow}>
        <div className={styles.legendLabel}>Origin (UTC{originOffset >= 0 ? '+' : ''}{originOffset})</div>
        {hoursOrigin.map(h => (
          <div key={'o'+h} className={styles.headerHour} style={{ gridColumn: 'span 2' }}>
            {`${h.toString().padStart(2,'0')}:00`}
          </div>
        ))}
      </div>

      <div className={styles.grid}>
        {days.map((d) => (
          <>
            <Row key={d.date} day={d} />
            {lastDay0Date === d.date && (
              <>
                <div className={styles.legendLabel}>Destination (UTC{destOffset >= 0 ? '+' : ''}{destOffset})</div>
                {hoursDest.map(h => (
                  <div key={'d'+d.date+':'+h} className={styles.headerHour} style={{ gridColumn: 'span 2' }}>
                    {`${h.toString().padStart(2,'0')}:00`}
                  </div>
                ))}
              </>
            )}
          </>
        ))}
      </div>

      {/* Bottom legend: UTC */}
      <div className={styles.legendRow}>
        <div className={styles.legendLabel}>UTC</div>
        {hoursUTC.map(h => (
          <div key={'u'+h} className={styles.headerHour} style={{ gridColumn: 'span 2' }}>
            {`${h.toString().padStart(2,'0')}:00`}
          </div>
        ))}
      </div>
    </div>
  )
}

function DebugSlotsGrid({ slots, originOffset, destOffset }: { slots: any[], originOffset: number, destOffset: number }) {
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

  const hoursUTC = Array.from({ length: 24 }, (_, i) => i)
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
  // CBTmin as red dot, Melatonin as 'M' marker
  return (
    <div className={classes.join(' ')}>
      {slot.is_cbtmin && <span className={styles.dot} />}
      {slot.is_melatonin && <span className={styles.mMark}>M</span>}
      {slot.is_travel && <span className={styles.tMark}>t</span>}
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
