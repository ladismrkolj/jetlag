import { NextRequest, NextResponse } from 'next/server'

type Inputs = {
  originOffset: number
  destOffset: number
  originSleepStart: string // HH:MM
  originSleepEnd: string   // HH:MM
  destSleepStart: string   // HH:MM
  destSleepEnd: string     // HH:MM
  travelStart: string      // datetime-local (origin local)
  travelEnd: string        // datetime-local (destination local)
  useMelatonin: boolean
  useLightDark: boolean
  useExercise: boolean
  preDays: number
}

export async function POST(req: NextRequest) {
  const body = (await req.json()) as Inputs
  try {
    const events = createJetLagTimetable(body)
    return NextResponse.json({ events })
  } catch (e: any) {
    return NextResponse.json({ error: e?.message ?? 'Error' }, { status: 400 })
  }
}

// --- Core logic (TypeScript port of backend rules) ---

function isoZ(d: Date) { return d.toISOString().replace(/\.\d{3}Z$/, 'Z') }
function clampHour(h: number) { let x = h % 24; if (x < 0) x += 24; return x }
function signedDeltaHours(curr: number, target: number) {
  let delta = ((target - curr + 12) % 24) - 12
  if (delta === -12) return 12
  return delta
}
function moveToward(curr: number, target: number, step: number, dirSign: number) {
  const remaining = Math.abs(signedDeltaHours(curr, target))
  if (remaining <= step) return clampHour(target)
  if (dirSign === 0) return clampHour(curr)
  return clampHour(curr + dirSign * step)
}

function parseHHMM(s: string) { const [h,m] = s.split(":").map(Number); return {h,m} }

function combineLocal(dateStr: string, offsetHours: number) {
  // dateStr: 'YYYY-MM-DDTHH:MM' local in given offset. Convert to UTC Date.
  const [dPart, tPart] = dateStr.split('T')
  const [Y,M,D] = dPart.split('-').map(Number)
  const [h,m] = tPart.split(':').map(Number)
  const utcMillis = Date.UTC(Y, (M-1), D, h - offsetHours, m)
  return new Date(utcMillis)
}

function midnightUTCForLocalDate(dateUTC: Date, offsetHours: number) {
  // Given a Date in UTC that represents some local instant (for ref), compute that local date's midnight in UTC.
  const localY = new Date(dateUTC.getTime() + offsetHours*3600*1000)
  const y = localY.getUTCFullYear(), m = localY.getUTCMonth(), d = localY.getUTCDate()
  const utc = new Date(Date.UTC(y, m, d, 0 - offsetHours, 0))
  return utc
}

function localDateFromUTC(dateUTC: Date, offsetHours: number) {
  const local = new Date(dateUTC.getTime() + offsetHours*3600*1000)
  return new Date(Date.UTC(local.getUTCFullYear(), local.getUTCMonth(), local.getUTCDate()))
}

function sleepWindowUTCForLocalDate(localDateUTC: Date, sleepStart: string, sleepEnd: string, offsetHours: number) {
  const {h:sh, m:sm} = parseHHMM(sleepStart)
  const {h:eh, m:em} = parseHHMM(sleepEnd)
  const start = new Date(localDateUTC.getTime() + (sh - offsetHours)*3600*1000 + sm*60*1000)
  let end = new Date(localDateUTC.getTime() + (eh - offsetHours)*3600*1000 + em*60*1000)
  if (end <= start) end = new Date(end.getTime() + 24*3600*1000)
  return [start, end] as const
}

function cbtHourUTCFromSleepEnd(sleepEnd: string, offsetHours: number, refLocalDateUTC: Date) {
  const {h:eh, m:em} = parseHHMM(sleepEnd)
  const wakeUTC = new Date(refLocalDateUTC.getTime() + (eh - offsetHours)*3600*1000 + em*60*1000)
  const cbtUTC = new Date(wakeUTC.getTime() - 3*3600*1000)
  return cbtUTC.getUTCHours() + cbtUTC.getUTCMinutes()/60
}

function createJetLagTimetable(inp: Inputs) {
  const {
    originOffset, destOffset,
    originSleepStart, originSleepEnd,
    destSleepStart, destSleepEnd,
    travelStart, travelEnd,
    useMelatonin, useLightDark, useExercise,
    preDays
  } = inp

  const travelStartUTC = combineLocal(travelStart, originOffset)
  const travelEndUTC = combineLocal(travelEnd, destOffset)
  // normalize interval (allow zero-length or reversed)
  let ts = travelStartUTC, te = travelEndUTC
  if (te.getTime() < ts.getTime()) { const tmp = ts; ts = te; te = tmp }

  // Day 0 local date in destination
  const day0LocalDateUTC = localDateFromUTC(te, destOffset)

  // Reference local dates for computing CBT hours
  const originRefLocalDateUTC = localDateFromUTC(travelStartUTC, originOffset)
  const destRefLocalDateUTC = localDateFromUTC(travelEndUTC, destOffset)

  const originCbtHour = cbtHourUTCFromSleepEnd(originSleepEnd, originOffset, originRefLocalDateUTC)
  const destCbtHour = cbtHourUTCFromSleepEnd(destSleepEnd, destOffset, destRefLocalDateUTC)

  const signedInitial = signedDeltaHours(originCbtHour, destCbtHour)
  const initialDiff = Math.abs(signedInitial)
  const phaseDirection = signedInitial > 0 ? 'delay' : (signedInitial < 0 ? 'advance' : 'aligned')
  const dirSign = signedInitial > 0 ? 1 : (signedInitial < 0 ? -1 : 0)
  const doShift = initialDiff >= 3.0

  const cbtEntries: Array<{ dayIndex: number, dt: Date }> = []
  let currentHour = originCbtHour

  // Preconditioning days in origin tz
  if (doShift && dirSign !== 0) {
    for (let i = preDays; i >= 1; i--) {
      const dLocalUTC = new Date(originRefLocalDateUTC.getTime() - i*24*3600*1000)
      const dayStartUTC = midnightUTCForLocalDate(dLocalUTC, originOffset)
      const remaining = Math.abs(signedDeltaHours(currentHour, destCbtHour))
      if (remaining > 0) {
        const step = 1.0 // preconditioning step per day when any method
        currentHour = moveToward(currentHour, destCbtHour, step, dirSign)
      }
      const dt = new Date(dayStartUTC.getTime() + currentHour*3600*1000)
      cbtEntries.push({ dayIndex: -i, dt })
    }
  }

  // Day 0
  const day0StartUTC = midnightUTCForLocalDate(day0LocalDateUTC, destOffset)
  cbtEntries.push({ dayIndex: 0, dt: new Date(day0StartUTC.getTime() + currentHour*3600*1000) })

  // Post arrival
  let remaining = Math.abs(signedDeltaHours(currentHour, destCbtHour))
  let dayIdx = 1
  if (doShift && dirSign !== 0) {
    while (remaining > 1e-6) {
      const dayStartUTC = midnightUTCForLocalDate(new Date(day0LocalDateUTC.getTime() + dayIdx*24*3600*1000), destOffset)
      const step = (useMelatonin || useLightDark || useExercise)
        ? (remaining > 3.0 ? 1.5 : 1.0)
        : (remaining > 3.0 ? 1.0 : 0.5)
      currentHour = moveToward(currentHour, destCbtHour, step, dirSign)
      const dt = new Date(dayStartUTC.getTime() + currentHour*3600*1000)
      cbtEntries.push({ dayIndex: dayIdx, dt })
      remaining = Math.abs(signedDeltaHours(currentHour, destCbtHour))
      dayIdx += 1
    }
  }

  // Build interventions and sleep
  const travelInt = [ts, te] as const
  const events: any[] = []
  const meta = { phase_direction: phaseDirection, signed_initial_diff_hours: signedInitial }

  // CBTmin and interventions
  for (const { dayIndex, dt } of cbtEntries) {
    events.push({ event: 'cbtmin', start: isoZ(dt), end: null, is_cbtmin: true, is_melatonin:false, is_light:false, is_dark:false, is_exercise:false, is_sleep:false, is_travel:false, day_index: dayIndex, ...meta })
    if (useMelatonin) {
      const m = new Date(dt.getTime() - 1.5*3600*1000)
      if (!(m >= travelInt[0] && m < travelInt[1])) {
        events.push({ event: 'melatonin', start: isoZ(m), end: null, is_cbtmin:false, is_melatonin:true, is_light:false, is_dark:false, is_exercise:false, is_sleep:false, is_travel:false, day_index: null, ...meta })
      }
    }
    if (useLightDark) {
      const l0 = new Date(dt.getTime() + 1*3600*1000), l1 = new Date(dt.getTime() + 2*3600*1000)
      const d0 = new Date(dt.getTime() - 1*3600*1000), d1 = new Date(dt.getTime() + 1*3600*1000)
      if (!(l0 < travelInt[1] && l1 > travelInt[0])) {
        events.push({ event: 'light', start: isoZ(l0), end: isoZ(l1), is_cbtmin:false, is_melatonin:false, is_light:true, is_dark:false, is_exercise:false, is_sleep:false, is_travel:false, day_index: null, ...meta })
      }
      if (!(d0 < travelInt[1] && d1 > travelInt[0])) {
        events.push({ event: 'dark', start: isoZ(d0), end: isoZ(d1), is_cbtmin:false, is_melatonin:false, is_light:false, is_dark:true, is_exercise:false, is_sleep:false, is_travel:false, day_index: null, ...meta })
      }
    }
    if (useExercise) {
      const e0 = new Date(dt.getTime() + 10*3600*1000), e1 = new Date(dt.getTime() + 11*3600*1000)
      if (!(e0 < travelInt[1] && e1 > travelInt[0])) {
        events.push({ event: 'exercise', start: isoZ(e0), end: isoZ(e1), is_cbtmin:false, is_melatonin:false, is_light:false, is_dark:false, is_exercise:true, is_sleep:false, is_travel:false, day_index: null, ...meta })
      }
    }
  }

  // Sleep windows: preconditioning in origin tz
  for (let i = preDays; i >= 1; i--) {
    const dLocalUTC = new Date(originRefLocalDateUTC.getTime() - i*24*3600*1000)
    const [s, e] = sleepWindowUTCForLocalDate(dLocalUTC, originSleepStart, originSleepEnd, originOffset)
    events.push({ event: 'sleep', start: isoZ(s), end: isoZ(e), is_cbtmin:false, is_melatonin:false, is_light:false, is_dark:false, is_exercise:false, is_sleep:true, is_travel:false, day_index: -i, ...meta })
  }
  // Day 0 onward in destination tz
  for (let i = 0; i < dayIdx; i++) {
    const dLocalUTC = new Date(day0LocalDateUTC.getTime() + i*24*3600*1000)
    const [s, e] = sleepWindowUTCForLocalDate(dLocalUTC, destSleepStart, destSleepEnd, destOffset)
    events.push({ event: 'sleep', start: isoZ(s), end: isoZ(e), is_cbtmin:false, is_melatonin:false, is_light:false, is_dark:false, is_exercise:false, is_sleep:true, is_travel:false, day_index: i, ...meta })
  }

  // Travel
  events.push({ event: 'travel', start: isoZ(ts), end: isoZ(te), is_cbtmin:false, is_melatonin:false, is_light:false, is_dark:false, is_exercise:false, is_sleep:false, is_travel:true, day_index: 0, ...meta })

  // Sort and return
  events.sort((a,b) => a.start.localeCompare(b.start))
  return events
}

