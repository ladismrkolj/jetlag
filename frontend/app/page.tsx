"use client"
import { Fragment, useEffect, useMemo, useState } from 'react'
import styles from './page.module.css'

type TzOffset = number // in hours, e.g. -5 for New York winter
type AdjustmentStartOption = 'after_arrival' | 'travel_start' | 'precondition'

const OFFSET_MIN = -12
const OFFSET_MAX = 14
const OFFSET_STEP = 0.25

const DEFAULT_ORIGIN_TZ = 'America/New_York'
const DEFAULT_DEST_TZ = 'Europe/Paris'

const FALLBACK_TIMEZONES = [
  'Pacific/Midway',
  'Pacific/Honolulu',
  'America/Anchorage',
  'America/Los_Angeles',
  'America/Denver',
  'America/Phoenix',
  'America/Chicago',
  'America/New_York',
  'America/Toronto',
  'America/Mexico_City',
  'America/Bogota',
  'America/Lima',
  'America/Caracas',
  'America/Santiago',
  'America/Argentina/Buenos_Aires',
  'America/Sao_Paulo',
  'America/St_Johns',
  'Atlantic/Azores',
  'Europe/London',
  'Europe/Dublin',
  'Europe/Lisbon',
  'Europe/Madrid',
  'Europe/Paris',
  'Europe/Berlin',
  'Europe/Rome',
  'Europe/Athens',
  'Europe/Helsinki',
  'Europe/Moscow',
  'Africa/Cairo',
  'Africa/Johannesburg',
  'Africa/Nairobi',
  'Asia/Jerusalem',
  'Asia/Dubai',
  'Asia/Karachi',
  'Asia/Kolkata',
  'Asia/Kathmandu',
  'Asia/Dhaka',
  'Asia/Bangkok',
  'Asia/Singapore',
  'Asia/Hong_Kong',
  'Asia/Taipei',
  'Asia/Shanghai',
  'Asia/Seoul',
  'Asia/Tokyo',
  'Australia/Perth',
  'Australia/Adelaide',
  'Australia/Sydney',
  'Pacific/Guadalcanal',
  'Pacific/Auckland',
  'Pacific/Chatham',
  'Pacific/Apia',
  'Pacific/Kiritimati',
] as const

const ADJUSTMENT_OPTIONS: { value: AdjustmentStartOption; label: string }[] = [
  { value: 'after_arrival', label: 'After arrival' },
  { value: 'travel_start', label: 'At start of travel' },
  { value: 'precondition', label: 'Before travel (precondition days)' },
]

export default function Page() {
  // Helpers
  const clamp = (n: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, n))
  const clampOffset = (value: number) => clamp(roundToQuarterHour(value), OFFSET_MIN, OFFSET_MAX)
  const fmtLocal = (d: Date) => {
    const pad = (x: number) => String(x).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
  }
  const noonPlusDays = (days: number) => {
    const d = new Date(); d.setDate(d.getDate() + days); d.setHours(12, 0, 0, 0); return fmtLocal(d)
  }

  const [originOffset, setOriginOffset] = useState<TzOffset>(-5)
  const [destOffset, setDestOffset] = useState<TzOffset>(1)
  const [originTimeZone, setOriginTimeZone] = useState<string>(DEFAULT_ORIGIN_TZ)
  const [destTimeZone, setDestTimeZone] = useState<string>(DEFAULT_DEST_TZ)
  const [originSleepStart, setOriginSleepStart] = useState('23:00')
  const [originSleepEnd, setOriginSleepEnd] = useState('07:00')
  const [destSleepStart, setDestSleepStart] = useState('23:00')
  const [destSleepEnd, setDestSleepEnd] = useState('07:00')
  const [travelStart, setTravelStart] = useState(noonPlusDays(1)) // tomorrow 12:00 local
  const [travelEnd, setTravelEnd] = useState(noonPlusDays(2))     // day after 12:00 local
  const [useMelatonin, setUseMelatonin] = useState(true)
  const [useLightDark, setUseLightDark] = useState(true)
  const [useExercise, setUseExercise] = useState(false)
  const [adjustmentStart, setAdjustmentStart] = useState<AdjustmentStartOption>('after_arrival')
  const [preDays, setPreDays] = useState(2)
  const [preDaysStr, setPreDaysStr] = useState<string>(String(2))
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

  const originReferenceDate = useMemo(() => pickReferenceDate(travelStart), [travelStart])
  const destReferenceDate = useMemo(() => pickReferenceDate(travelEnd), [travelEnd])
  const [timezoneNames, setTimezoneNames] = useState<string[]>(() => getAllTimeZoneNames(true))
  const originTimeZoneOptions = useMemo(() => buildTimeZoneOptions(timezoneNames, originReferenceDate), [timezoneNames, originReferenceDate])
  const destTimeZoneOptions = useMemo(() => buildTimeZoneOptions(timezoneNames, destReferenceDate), [timezoneNames, destReferenceDate])

  useEffect(() => {
    // For beta: show on every reload for now
    setBetaOpen(true)
  }, [])

  useEffect(() => {
    // Refresh with the full Intl-provided list once we are on the client
    const names = getAllTimeZoneNames()
    if (!names.length) return
    setTimezoneNames(prev => {
      if (prev.length === names.length && prev.every((v, i) => v === names[i])) return prev
      return names
    })
  }, [])

  useEffect(() => {
    const fallback = originTimeZoneOptions[0]
    if (!fallback) return
    if (!originTimeZoneOptions.some(opt => opt.value === originTimeZone)) {
      setOriginTimeZone(fallback.value)
    }
  }, [originTimeZoneOptions, originTimeZone])

  useEffect(() => {
    const fallback = destTimeZoneOptions[0]
    if (!fallback) return
    if (!destTimeZoneOptions.some(opt => opt.value === destTimeZone)) {
      setDestTimeZone(fallback.value)
    }
  }, [destTimeZoneOptions, destTimeZone])

  useEffect(() => {
    if (!originTimeZone) return
    const offset = getTimeZoneOffsetHours(originTimeZone, originReferenceDate ?? undefined)
    if (offset == null) return
    const rounded = clampOffset(offset)
    setOriginOffset(prev => Math.abs(prev - rounded) > 1e-6 ? rounded : prev)
  }, [originTimeZone, originReferenceDate])

  useEffect(() => {
    if (!destTimeZone) return
    const offset = getTimeZoneOffsetHours(destTimeZone, destReferenceDate ?? undefined)
    if (offset == null) return
    const rounded = clampOffset(offset)
    setDestOffset(prev => Math.abs(prev - rounded) > 1e-6 ? rounded : prev)
  }, [destTimeZone, destReferenceDate])

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
          adjustmentStart,
          preDays,
        })
      })
      if (!res.ok) throw new Error(`API error: ${res.status}`)
      const data = await res.json()
      const receivedEvents = Array.isArray(data.events) ? data.events : null
      setEvents(receivedEvents)
      if (receivedEvents) {
        // Update the displayed legends only upon successful calculation
        setLegendOriginOffset(originOffset)
        setLegendDestOffset(destOffset)
      } else {
        setLegendOriginOffset(originOffset)
        setLegendDestOffset(destOffset)
      }
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
          <label>Origin time zone</label>
          <select value={originTimeZone} onChange={e => setOriginTimeZone(e.target.value)}>
            {originTimeZoneOptions.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <label>Destination time zone</label>
          <select value={destTimeZone} onChange={e => setDestTimeZone(e.target.value)}>
            {destTimeZoneOptions.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
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
          <div className={styles.adjustmentControl}>
            <label htmlFor="adjustmentStart">Start adjustments</label>
            <select id="adjustmentStart" value={adjustmentStart} onChange={e => setAdjustmentStart(e.target.value as AdjustmentStartOption)}>
              {ADJUSTMENT_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div className={styles.preDaysControl}>
            <label htmlFor="preDaysInput">Precondition days</label>
            <input
              id="preDaysInput"
              type="number"
              min={0}
              max={11}
              inputMode="numeric"
              value={preDaysStr}
              disabled={adjustmentStart !== 'precondition'}
              onChange={e => {
                const next = e.target.value
                setPreDaysStr(next)
                const parsed = parseInt(next || '', 10)
                if (!Number.isNaN(parsed)) {
                  const clamped = clamp(parsed, 0, 11)
                  if (clamped !== preDays) setPreDays(clamped)
                }
              }}
              onBlur={() => {
                const p = parseInt(preDaysStr || '', 10)
                const v = clamp(Number.isNaN(p) ? preDays : p, 0, 11)
                setPreDays(v)
                setPreDaysStr(String(v))
              }}
            />
          </div>
        </div>
        <div className={styles.actions}>
          <button type="submit" disabled={loading}>{loading ? 'Calculating…' : 'Calculate'}</button>
          <button type="button" onClick={() => { if (typeof window !== 'undefined') window.print() }}>
            Print this page
          </button>
          
        </div>
      </form>

      {error && <p className={styles.error}>{error}</p>}

      {events && (
        <TimetableGrid events={events} originOffset={legendOriginOffset} destOffset={legendDestOffset} />
      )}

      <section className={styles.explanation}>
        <h2>Behind the Recommendation</h2>

        <h3>What the App Is Trying to Do</h3>
        <p>
          Jet lag occurs when your internal circadian phase (the “body clock”) is out of sync with the new local time. 
          The fastest way to reduce symptoms is to <strong>shift the clock</strong> efficiently while avoiding timing mistakes that push it the wrong way. 
          Our scheduler uses three main levers:
        </p>
        <ul>
          <li><strong>Light</strong> (seek vs avoid)</li>
          <li><strong>Melatonin</strong> (dose and timing)</li>
          <li><strong>Exercise</strong> (being active)</li>
        </ul>
        <p>
          All timings are derived from peer-reviewed phase-response curves (PRCs) to light and melatonin, 
          with practical rules distilled from&nbsp;<a href="https://www.frontiersin.org/articles/10.3389/fphys.2019.00927/full" target="_blank" rel="noreferrer">Roach &amp; Sargent (2019)</a><sup>[1]</sup>.
        </p>

        <h3>Key Physiology (Why Timing Matters)</h3>
        <ul>
          <li>
            <strong>CBTmin (core body temperature minimum)</strong> is the circadian “pivot.”  
            Light in the ~12 h before CBTmin induces <strong>phase delays</strong>, while light in the ~12 h after CBTmin induces <strong>phase advances</strong>.  
            The largest shifts occur with light ~3–6 h either side of CBTmin&nbsp;
            (<a href="https://www.science.org/doi/10.1126/science.2734611" target="_blank" rel="noreferrer">Czeisler et al., 1989</a><sup>[2]</sup>; 
            <a href="https://physoc.onlinelibrary.wiley.com/doi/10.1113/jphysiol.2003.040477" target="_blank" rel="noreferrer">Khalsa et al., 2003</a><sup>[3]</sup>).
          </li>
          <li>
            <strong>Melatonin has its own PRC:</strong>  
            Maximum <strong>advances</strong> occur when taken ~11.5 h before CBTmin (~6.5 h before habitual bedtime);  
            maximum <strong>delays</strong> occur when taken ~4 h after CBTmin (~1 h after habitual wake).&nbsp; 
            (<a href="https://doi.org/10.1113/jphysiol.2007.143180" target="_blank" rel="noreferrer">Burgess et al., 2008</a><sup>[4]</sup>)
          </li>
        </ul>

        <h3>How the App Generates Your Plan</h3>
        <ol>
          <li><strong>Estimate starting phase:</strong> CBTmin is approximated as ~2–3 h before habitual wake time.</li>
          <li><strong>Compute target shift:</strong> Direction and magnitude of time zone change determine whether phase advances (eastward) or delays (westward) are scheduled.</li>
          <li><strong>Map PRCs to actions:</strong>  
            <ul>
              <li><strong>Light:</strong> Seek bright light in the appropriate PRC zone (advance vs delay) and avoid it in the opposite zone.</li>
              <li><strong>Melatonin (optional):</strong> Scheduled near the PRC peak for the desired shift direction, avoiding dead zones.</li>
              <li><strong>Exercise (optional):</strong> Scheduled near the PRC peak, placed to reinforce the desired shift.</li>
            </ul>
          </li>
          <li><strong>Apply constraints:</strong> Daily phase shifts are capped (~1–2 h/day), and travel demands are integrated.</li>
        </ol>

        <h3>Why These Specific Timings Work</h3>
        <p>
          <strong>Eastward travel:</strong> Morning light (post-CBTmin) plus evening melatonin accelerates advances and blocks delays.  
          <br />
          <strong>Westward travel:</strong> Evening/night light (pre-CBTmin) plus morning light avoidance delay the clock efficiently. Melatonin may be used but is less critical.
        </p>

        <h3>Risks and Side Effects</h3>
        <p>
          <strong>Melatonin (3 mg immediate-release):</strong> Possible drowsiness, vivid dreams, headache, GI upset. 
          May interact with anticoagulants, sedatives, antihypertensives, immunosuppressants. Not well studied in pregnancy, lactation, epilepsy, or autoimmune disease. 
          Avoid activities requiring alertness if drowsy.
        </p>
        <p>
          <strong>Light:</strong> Nighttime light can impair sleep if mistimed.
        </p>
        <p>
          <strong>Sleep timing, naps, caffeine:</strong> Early-afternoon naps can reduce fatigue without harming night sleep. Caffeine aids alertness but does not shift the circadian phase.
        </p>

        <h3>Limitations</h3>
        <ul>
          <li>CBTmin is estimated, not measured—individual variation can cause mismatches.</li>
          <li>PRC data are averages; responses vary by genetics, age, light history, season.</li>
          <li>Light intensity and exposure vary in real-world conditions (clouds, indoor light).</li>
          <li>Flight schedules and commitments can constrain optimal timing.</li>
          <li>Evidence is based on specific melatonin doses/forms (3 mg immediate-release).</li>
          <li>Not a medical device—consult a clinician for medical conditions.</li>
        </ul>

        <h3>Summary</h3>
        <p>
          Your personalized schedule is built by estimating your circadian phase (CBTmin), 
          calculating the advance or delay required, and aligning light, melatonin, exercise and sleep 
          to the most effective PRC zones while avoiding exposure that would counteract the shift. 
          The underlying science is drawn from laboratory circadian studies and expert synthesis. 
          Outcomes will vary between individuals.
        </p>

        <hr />

        <h4>References</h4>
        <ol>
          <li>Roach GD, Sargent C. Interventions to Minimize Jet Lag After Westward and Eastward Flight. <em>Front Physiol</em>. 2019;10:927. <a href="https://www.frontiersin.org/articles/10.3389/fphys.2019.00927/full" target="_blank" rel="noreferrer">Link</a></li>
          <li>Czeisler CA, et al. Bright light induction of strong (type 0) resetting of the human circadian pacemaker. <em>Science</em>. 1989;244(4910):1328–1333. <a href="https://www.science.org/doi/10.1126/science.2734611" target="_blank" rel="noreferrer">Link</a></li>
          <li>Khalsa SB, et al. A phase response curve to single bright light pulses in human subjects. <em>J Physiol</em>. 2003;549(Pt 3):945–952. <a href="https://physoc.onlinelibrary.wiley.com/doi/10.1113/jphysiol.2003.040477" target="_blank" rel="noreferrer">Link</a></li>
          <li>Burgess HJ, et al. Human phase response curves to three days of daily melatonin: 0.5 mg versus 3.0 mg. <em>J Clin Endocrinol Metab</em>. 2008;93(12):4655–4660. <a href="https://doi.org/10.1113/jphysiol.2007.143180" target="_blank" rel="noreferrer">Link</a></li>
        </ol>
      </section>


      {events && (
        <div className={styles.emojiBand}>
          <button className={styles.emojiButton} aria-label="Love it" onClick={() => { setQuickRating('heart'); setQuickOpen(true); setQuickMessage(null) }}>❤️</button>
          <button className={styles.emojiButton} aria-label="Great" onClick={() => { setQuickRating('party'); setQuickOpen(true); setQuickMessage(null) }}>🎉</button>
          <button className={styles.emojiButton} aria-label="Not good" onClick={() => { setQuickRating('down'); setQuickOpen(true); setQuickMessage(null) }}>👎</button>
        </div>
      )}

      <footer className={styles.siteFooter}>
        <div className={styles.footerMeta}>
          <span className={styles.footerText}>
            © {new Date().getFullYear()} Jet Lag Planner. Licensed under{' '}
            <a className={styles.footerLink} href="https://github.com/ladismrkolj/jetlag/blob/main/LICENSE" target="_blank" rel="noreferrer">Business Source License 1.1</a>.
          </span>
        </div>
        <button className={styles.reportBtn} type="button" onClick={() => { setReportOpen(true); setReportMessage(null) }}>
          Report a problem or suggestion
        </button>
      </footer>

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
                      travelStart, travelEnd, useMelatonin, useLightDark, useExercise, adjustmentStart, preDays
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
                    inputs:{ originOffset, destOffset, preDays, adjustmentStart },
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
  // Group events by UTC date; 48 columns (30-minute slots)
  const days = useMemo(() => groupEventsByUTCDate(events), [events])
  const hoursOrigin = hourLabels(originOffset)
  const hoursDest = hourLabels(destOffset)

  const formatHour = (hour: number) => hour.toString().padStart(2, '0')

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
      <div className={styles.gridScroller}>
        <div className={styles.legendRow}>
          <div className={styles.timeRowLabel}>Origin (UTC{originOffset >= 0 ? '+' : ''}{originOffset})</div>
          {hoursOrigin.map((h, idx) => (
            <div key={`origin:${idx}`} className={styles.headerHour} style={{ gridColumn: 'span 2' }}>
              {formatHour(h)}
            </div>
          ))}
          <div className={styles.timeRowLabelEnd}>Origin (UTC{originOffset >= 0 ? '+' : ''}{originOffset})</div>
        </div>

        <div className={styles.grid}>
          {days.map(day => (
            <Row key={day.date} day={day} />
          ))}
        </div>

        <div className={styles.legendRow}>
          <div className={styles.timeRowLabel}>Destination (UTC{destOffset >= 0 ? '+' : ''}{destOffset})</div>
          {hoursDest.map((h, idx) => (
            <div key={`dest:${idx}`} className={styles.headerHour} style={{ gridColumn: 'span 2' }}>
              {formatHour(h)}
            </div>
          ))}
          <div className={styles.timeRowLabelEnd}>Destination (UTC{destOffset >= 0 ? '+' : ''}{destOffset})</div>
        </div>
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
            {d.slots.map((slot: any, i: number) => (
              <Cell key={d.date+':'+i} slot={slot} slotIndex={i} />
            ))}
          </>
        ))}
      </div>
    </div>
  )
}

function Row({ day }: { day: ReturnType<typeof groupEventsByUTCDate>[number] }) {
  return (
    <Fragment>
      <div className={styles.rowLabel}>{day.date}</div>
      {day.slots.map((slot: any, i: number) => (
        <Cell key={i} slot={slot} slotIndex={i} />
      ))}
      <div className={styles.rowLabelEnd}>{day.date}</div>
    </Fragment>
  )
}

function Cell({ slot, slotIndex }: { slot: ReturnType<typeof groupEventsByUTCDate>[number]['slots'][number], slotIndex: number }) {
  const classes = [styles.cell]
  if (slotIndex % 2 === 0) classes.push(styles.hourStart)
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
  const parseUTC = (s: string | null) => {
    if (!s) return null
    const str = String(s)
    return /Z$|[+-]\d{2}:\d{2}$/.test(str) ? new Date(str) : new Date(str + 'Z')
  }
  if (!events.length) return [] as any[]
  const starts = events.map(e => parseUTC(e.start)).filter(Boolean) as Date[]
  const ends = events.map(e => parseUTC(e.end)).filter(Boolean) as Date[]
  const minStart = new Date(Math.min(...starts.map(d => d.getTime())))
  const maxEnd = ends.length ? new Date(Math.max(...ends.map(d => d.getTime()))) : new Date(Math.max(...starts.map(d => d.getTime())))
  const startDay = new Date(Date.UTC(minStart.getUTCFullYear(), minStart.getUTCMonth(), minStart.getUTCDate()))
  const endDay = new Date(Date.UTC(maxEnd.getUTCFullYear(), maxEnd.getUTCMonth(), maxEnd.getUTCDate()))
  // Drop the last day row as requested
  const lastRowDay = new Date(Math.max(startDay.getTime(), endDay.getTime() - 24*3600*1000))
  const days: { date: string, slots: any[] }[] = []
  for (let d = new Date(startDay); d <= lastRowDay; d = new Date(d.getTime() + 24*3600*1000)) {
    const dateStr = d.toISOString().slice(0,10)
    const slots = [] as any[]
    for (let i = 0; i < 48; i++) {
      const slotStart = new Date(d.getTime() + i*30*60*1000)
      const slotEnd = new Date(d.getTime() + (i+1)*30*60*1000)
      const flags = { is_sleep:false, is_light:false, is_dark:false, is_travel:false, is_exercise:false, is_melatonin:false, is_cbtmin:false }
      for (const e of events) {
        const es = parseUTC(e.start)
        const ee = parseUTC(e.end)
        let occurs = false
        if (ee == null && es) {
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

type TimeZoneOption = { value: string, label: string, offset: number | null }

function getAllTimeZoneNames(forceFallback = false): string[] {
  if (!forceFallback && typeof Intl !== 'undefined' && typeof (Intl as any).supportedValuesOf === 'function') {
    try {
      const values = (Intl as any).supportedValuesOf('timeZone') as string[]
      if (Array.isArray(values) && values.length) return values
    } catch {}
  }
  return Array.from(new Set(FALLBACK_TIMEZONES))
}

function buildTimeZoneOptions(names: string[], referenceDate: Date | null): TimeZoneOption[] {
  const ref = referenceDate ?? new Date()
  const options: TimeZoneOption[] = []
  const seen = new Set<string>()
  for (const name of names) {
    if (!name || seen.has(name)) continue
    seen.add(name)
    const offset = getTimeZoneOffsetHours(name, ref)
    options.push({ value: name, label: formatTimeZoneLabel(name, offset), offset })
  }
  options.sort((a, b) => {
    const ao = a.offset ?? Number.POSITIVE_INFINITY
    const bo = b.offset ?? Number.POSITIVE_INFINITY
    if (ao !== bo) return ao - bo
    return a.label.localeCompare(b.label)
  })
  return options
}

function getTimeZoneOffsetHours(timeZone: string, referenceDate?: Date | null): number | null {
  try {
    const date = referenceDate ?? new Date()
    const minutes = getTimeZoneOffsetMinutes(timeZone, date)
    if (!Number.isFinite(minutes)) return null
    return minutes / 60
  } catch {
    return null
  }
}

function getTimeZoneOffsetMinutes(timeZone: string, date: Date): number {
  const dtf = new Intl.DateTimeFormat('en-US', {
    timeZone,
    hour12: false,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
  const parts = dtf.formatToParts(date)
  const map = new Map<string, string>()
  for (const part of parts) {
    map.set(part.type, part.value)
  }
  const year = Number(map.get('year'))
  const month = Number(map.get('month'))
  const day = Number(map.get('day'))
  const hour = Number(map.get('hour'))
  const minute = Number(map.get('minute'))
  const second = Number(map.get('second'))
  const asUTC = Date.UTC(year, month - 1, day, hour, minute, second)
  return (asUTC - date.getTime()) / 60000
}

function roundToQuarterHour(value: number): number {
  return Math.round(value * 4) / 4
}

function formatOffsetForDisplay(offset: number): string {
  const totalMinutes = Math.round(Math.abs(offset) * 60)
  const sign = offset >= 0 ? '+' : '-'
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return `UTC${sign}${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
}

function formatTimeZoneLabel(timeZone: string, offset: number | null): string {
  const readable = timeZone.replace(/_/g, ' ')
  return offset == null ? readable : `${readable} (${formatOffsetForDisplay(offset)})`
}

function pickReferenceDate(value: string | null | undefined): Date | null {
  if (!value) return null
  const [datePart] = String(value).split('T')
  if (!datePart) return null
  const parts = datePart.split('-')
  if (parts.length < 3) return null
  const [yearStr, monthStr, dayStr] = parts
  const year = Number(yearStr)
  const month = Number(monthStr)
  const day = Number(dayStr)
  if ([year, month, day].some(v => Number.isNaN(v))) return null
  return new Date(Date.UTC(year, month - 1, day, 12, 0, 0))
}
