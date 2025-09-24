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
  const [shiftOnTravelDays, setShiftOnTravelDays] = useState(false)
  const [preDays, setPreDays] = useState(2)
  // Freeze legend offsets to last-calculated values
  const [legendOriginOffset, setLegendOriginOffset] = useState<TzOffset>(-5)
  const [legendDestOffset, setLegendDestOffset] = useState<TzOffset>(1)
  const [events, setEvents] = useState<any[] | null>(null)
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
          shiftOnTravelDays,
          preDays,
        })
      })
      if (!res.ok) throw new Error(`API error: ${res.status}`)
      const data = await res.json()
      setEvents(data.events)
      // Update the displayed legends only upon successful calculation
      setLegendOriginOffset(originOffset)
      setLegendDestOffset(destOffset)
      // reset any ad-hoc debug views if present
    } catch (err: any) {
      setError(err.message || 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  // removed sample slots loader

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
          <label title="Allow shifting/activities around travel when possible."><input type="checkbox" checked={shiftOnTravelDays} onChange={e => setShiftOnTravelDays(e.target.checked)} /> Shift on travel days</label>
        </div>
        <div className={styles.actions}>
          <button type="submit" disabled={loading}>{loading ? 'Calculating…' : 'Calculate'}</button>
          
        </div>
      </form>

      {error && <p className={styles.error}>{error}</p>}

      {events && <TimetableGrid events={events} originOffset={legendOriginOffset} destOffset={legendDestOffset} />}

      {events && (
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
                      travelStart, travelEnd, useMelatonin, useLightDark, useExercise, shiftOnTravelDays, preDays
                    },
                    data: events ?? null,
                    userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown',
                    url: typeof location !== 'undefined' ? location.href : 'unknown',
                    screenshot,
                    email: (reportEmail || '').trim() || null,
                  }
                  // attach full rasterized slots
                  try {
                    let slotsPayload: any[] = []
                    if (Array.isArray(events) && events.length) {
                      const days = groupEventsByLocalDate(events, legendDestOffset)
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
                    inputs:{ originOffset, destOffset, preDays, shiftOnTravelDays },
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
  // Group events by destination local date; 48 columns (30-minute slots)
  const days = useMemo(() => groupEventsByLocalDate(events, destOffset), [events, destOffset])
  const hoursUTC = Array.from({ length: 24 }, (_, i) => i)
  const hoursOrigin = hourLabels(originOffset)
  const hoursDest = hourLabels(destOffset)

  const day0LocalDate = useMemo(() => {
    // Day 0 is destination local date of travelEnd
    try {
      const travel = events.find(e => e && e.event === 'travel' && typeof e.end === 'string')
      if (!travel) return days.length ? days[0].date : null
      const te = new Date(String(travel.end))
      const local = new Date(te.getTime() + destOffset*3600*1000)
      return local.toISOString().slice(0,10)
    } catch {
      return days.length ? days[0].date : null
    }
  }, [events, destOffset, days])

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
      {/* Top legend: Origin local time (shifted left by half slot) */}
      <div className={styles.legendRow}>
        <div className={styles.legendLabel}>Origin (UTC{originOffset >= 0 ? '+' : ''}{originOffset})</div>
        {hoursOrigin.map((h, idx) => (
          <div key={'o'+idx} className={styles.headerHour + ' ' + styles.headerHourShift} style={{ gridColumn: 'span 2' }}>
            {`${h.toString().padStart(2,'0')}:00`}
          </div>
        ))}
        <div className={styles.headerHourOverlay}>{`${hoursOrigin[0].toString().padStart(2,'0')}:00`}</div>
      </div>

      <div className={styles.grid}>
        {days.map((d) => (
          <>
            <Row key={d.date} day={d} />
            {day0LocalDate === d.date && (
              <>
                <div className={styles.legendLabel}>Destination (UTC{destOffset >= 0 ? '+' : ''}{destOffset})</div>
                {hoursDest.map((h, idx) => (
                  <div key={'d'+d.date+':'+idx} className={styles.headerHour + ' ' + styles.headerHourShift} style={{ gridColumn: 'span 2' }}>
                    {`${h.toString().padStart(2,'0')}:00`}
                    {idx === 23 && (
                      <span className={styles.headerHourDupRight}>{`${hoursDest[0].toString().padStart(2,'0')}:00`}</span>
                    )}
                  </div>
                ))}
              </>
            )}
          </>
        ))}
      </div>

      {/* Bottom legend: UTC (aligns with row columns), shifted left by half slot */}
      <div className={styles.legendRow}>
        <div className={styles.legendLabel}>UTC</div>
        {hoursUTC.map((h, idx) => (
          <div key={'u'+idx} className={styles.headerHour + ' ' + styles.headerHourShift} style={{ gridColumn: 'span 2' }}>
            {`${h.toString().padStart(2,'0')}:00`}
          </div>
        ))}
        <div className={styles.headerHourOverlay}>{`${hoursUTC[0].toString().padStart(2,'0')}:00`}</div>
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
  const hours = hoursUTC
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

function Row({ day }: { day: ReturnType<typeof groupEventsByLocalDate>[number] }) {
  return (
    <>
      <div className={styles.rowLabel}>{day.date}</div>
      {day.slots.map((slot, i) => (
        <Cell key={i} slot={slot} />
      ))}
    </>
  )
}

function Cell({ slot }: { slot: ReturnType<typeof groupEventsByLocalDate>[number]['slots'][number] }) {
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

function groupEventsByLocalDate(events: any[], destOffset: number) {
  // Build 30-minute slots for each DESTINATION-local day spanned by events (00–24 local)
  const parse = (s: string | null) => (s ? new Date(s) : null)
  if (!events.length) return [] as any[]
  const starts = events.map(e => parse(e.start)).filter(Boolean) as Date[]
  const ends = events.map(e => parse(e.end)).filter(Boolean) as Date[]
  const minStartUTC = new Date(Math.min(...starts.map(d => d.getTime())))
  const latestStartUTC = new Date(Math.max(...starts.map(d => d.getTime())))
  const maxEndUTC = ends.length ? new Date(Math.max(...ends.map(d => d.getTime()))) : latestStartUTC

  // Convert UTC instants to destination local dates (as UTC Date at local midnight)
  const toLocalDateUTC = (dUTC: Date) => {
    const local = new Date(dUTC.getTime() + destOffset*3600*1000)
    return new Date(Date.UTC(local.getUTCFullYear(), local.getUTCMonth(), local.getUTCDate()))
  }
  // If there is any CBTmin event, start table at that day (destination local midnight)
  const firstCbt = (events as any[]).filter(e => e && e.event === 'cbtmin' && typeof e.start === 'string')
    .map(e => new Date(String(e.start)))
    .sort((a,b)=>a.getTime()-b.getTime())[0]
  const startLocalDateUTC = firstCbt ? toLocalDateUTC(firstCbt) : toLocalDateUTC(minStartUTC)
  const endLocalDateUTC = toLocalDateUTC(maxEndUTC)
  // Show one less row than the total calculated span: drop the last day row
  const lastRowLocalDateUTC = new Date(Math.max(startLocalDateUTC.getTime(), endLocalDateUTC.getTime() - 24*3600*1000))

  const days: { date: string, slots: any[] }[] = []
  for (let dLocal = new Date(startLocalDateUTC); dLocal <= lastRowLocalDateUTC; dLocal = new Date(dLocal.getTime() + 24*3600*1000)) {
    // local midnight in UTC by subtracting offset
    const dayStartUTC = new Date(dLocal.getTime() - destOffset*3600*1000)
    const dateStr = dLocal.toISOString().slice(0,10) // local date label
    const slots = [] as any[]
    for (let i = 0; i < 48; i++) {
      const slotStart = new Date(dayStartUTC.getTime() + i*30*60*1000)
      const slotEnd = new Date(dayStartUTC.getTime() + (i+1)*30*60*1000)
      // aggregate flags if any event overlaps
      const flags = { is_sleep:false, is_light:false, is_dark:false, is_travel:false, is_exercise:false, is_melatonin:false, is_cbtmin:false }
      for (const e of events) {
        const es = parse(e.start)
        const ee = parse(e.end)
        let occurs = false
        if (ee == null && es) {
          // Include point events on [start,end). Edge-case: if exactly at day end, include in last slot.
          occurs = (es >= slotStart && es < slotEnd) || (i === 47 && es.getTime() === slotEnd.getTime())
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
