export type JetLagInputs = {
  originOffset: number
  destOffset: number
  originSleepStart: string
  originSleepEnd: string
  destSleepStart: string
  destSleepEnd: string
  travelStart: string
  travelEnd: string
  useMelatonin: boolean
  useLightDark: boolean
  useExercise: boolean
  preDays: number
  adjustmentStart: 'after_arrival' | 'travel_start' | 'precondition' | 'precondition_with_travel'
}

export type JetLagEvent = {
  event: string
  start: string
  end: string | null
  is_cbtmin: boolean
  is_melatonin: boolean
  is_light: boolean
  is_dark: boolean
  is_exercise: boolean
  is_sleep: boolean
  is_travel: boolean
  day_index: number | null
  phase_direction: string
  signed_initial_diff_hours: number
}

const MS_MINUTE = 60 * 1000
const MS_HOUR = 60 * MS_MINUTE
const MS_DAY = 24 * MS_HOUR
const EPSILON = 1e-6

type Interval = [Date, Date]

type InterventionSchedule = {
  melatonin: { enabled: boolean; at: Date }
  exercise: { enabled: boolean; window: Interval }
  light: { enabled: boolean; window: Interval }
  dark: { enabled: boolean; window: Interval }
}

type CBTEntry = {
  cbtmin: Date
  interventions: InterventionSchedule
}

const PRESETS = {
  default: {
    melatonin_advance: -11.5,
    melatonin_delay: 4,
    exercise_advance: [0, 3] as [number, number],
    exercise_delay: [-3, 0] as [number, number],
    light_advance: [0, 6] as [number, number],
    light_delay: [-6, 0] as [number, number],
    dark_advance: [-6, 0] as [number, number],
    dark_delay: [0, 6] as [number, number],
  },
}

const mod = (value: number, modulus: number) => ((value % modulus) + modulus) % modulus

const parseHHMM = (value: string) => {
  const match = /^([01]\d|2[0-3]):([0-5]\d)$/.exec(value)
  if (!match) throw new Error(`invalid HH:MM time: ${value}`)
  const hours = Number(match[1])
  const minutes = Number(match[2])
  return hours * 60 + minutes
}

const parseLocalDateTime = (value: string) => {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value)
  if (!match) throw new Error(`invalid datetime-local: ${value}`)
  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  const hour = Number(match[4])
  const minute = Number(match[5])
  return new Date(Date.UTC(year, month - 1, day, hour, minute, 0, 0))
}

const addHours = (date: Date, hours: number) => new Date(date.getTime() + hours * MS_HOUR)
const addDays = (date: Date, days: number) => new Date(date.getTime() + days * MS_DAY)

const normalizeMinutes = (minutes: number) => mod(minutes, 24 * 60)
const sumTimeDelta = (timeMinutes: number, deltaHours: number) =>
  normalizeMinutes(timeMinutes + deltaHours * 60)

const hoursFromMinutes = (minutes: number) => minutes / 60

const toIso = (dt: Date) => dt.toISOString().replace('.000Z', 'Z')

const midnightForDatetime = (dt: Date) =>
  new Date(Date.UTC(dt.getUTCFullYear(), dt.getUTCMonth(), dt.getUTCDate(), 0, 0, 0, 0))

const combineDateMinutes = (date: Date, minutesFromMidnight: number) => {
  const midnight = Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate(), 0, 0, 0, 0)
  return new Date(midnight + minutesFromMidnight * MS_MINUTE)
}

const intersectionHours = (interval1: Interval, interval2: Interval) => {
  const [start1, end1] = interval1
  const [start2, end2] = interval2
  const latestStart = Math.max(start1.getTime(), start2.getTime())
  const earliestEnd = Math.min(end1.getTime(), end2.getTime())
  if (latestStart >= earliestEnd) return 0
  return (earliestEnd - latestStart) / MS_HOUR
}

const isInsideInterval = (ts: Date, interval: Interval) => ts >= interval[0] && ts < interval[1]

const subtractIntervals = (interval: Interval, exclusions: Interval[]) => {
  const [start, end] = interval
  if (start >= end) return []
  if (exclusions.length === 0) return [[start, end]] as Interval[]
  const sorted = [...exclusions].sort((a, b) => a[0].getTime() - b[0].getTime())
  const result: Interval[] = []
  let cursor = start
  for (const [exclusionStart, exclusionEnd] of sorted) {
    if (exclusionEnd <= cursor) continue
    if (exclusionStart >= end) break
    if (exclusionStart > cursor) {
      result.push([cursor, new Date(Math.min(exclusionStart.getTime(), end.getTime()))])
    }
    cursor = new Date(Math.max(cursor.getTime(), exclusionEnd.getTime()))
    if (cursor >= end) break
  }
  if (cursor < end) {
    result.push([cursor, end])
  }
  return result
}

const nextInterval = (time: Date, interval: [number, number], filterWindow: Interval | null = null) => {
  const [startTimeMinutes, endTimeMinutes] = interval
  let startDt = combineDateMinutes(time, startTimeMinutes)
  let endDt = combineDateMinutes(time, endTimeMinutes)

  if (endDt <= startDt) {
    endDt = addDays(endDt, 1)
  }

  if (startDt <= time) {
    if (endDt > time) {
      startDt = time
    } else {
      startDt = addDays(startDt, 1)
      endDt = addDays(endDt, 1)
    }
  }

  if (filterWindow) {
    const [filterStart, filterEnd] = filterWindow
    const overlapStart = new Date(Math.max(startDt.getTime(), filterStart.getTime()))
    const overlapEnd = new Date(Math.min(endDt.getTime(), filterEnd.getTime()))

    if (overlapStart < overlapEnd) {
      if (overlapStart <= startDt && overlapEnd >= endDt) {
        return [null, null]
      }
      if (overlapStart <= startDt) {
        startDt = overlapEnd
      } else if (overlapEnd >= endDt) {
        endDt = overlapStart
      } else {
        endDt = overlapStart
      }
    }
  }

  if (startDt >= endDt) {
    return [null, null]
  }

  return [startDt, endDt]
}

const signedDiffHours = (destMinutes: number, currentMinutes: number) => {
  const diff = hoursFromMinutes(destMinutes - currentMinutes)
  let norm = mod(diff + 12, 24) - 12
  if (norm === -12) norm = 12
  return norm
}

const buildEvent = (
  event: JetLagEvent['event'],
  start: Date,
  end: Date | null,
  flags: {
    is_cbtmin?: boolean
    is_melatonin?: boolean
    is_light?: boolean
    is_dark?: boolean
    is_exercise?: boolean
    is_sleep?: boolean
    is_travel?: boolean
  },
  meta: { phase_direction: string; signed_initial_diff_hours: number },
): JetLagEvent => ({
  event,
  start: toIso(start),
  end: end ? toIso(end) : null,
  is_cbtmin: Boolean(flags.is_cbtmin),
  is_melatonin: Boolean(flags.is_melatonin),
  is_light: Boolean(flags.is_light),
  is_dark: Boolean(flags.is_dark),
  is_exercise: Boolean(flags.is_exercise),
  is_sleep: Boolean(flags.is_sleep),
  is_travel: Boolean(flags.is_travel),
  day_index: null,
  phase_direction: meta.phase_direction,
  signed_initial_diff_hours: meta.signed_initial_diff_hours,
})

export const createJetLagTimetable = (inputs: JetLagInputs): JetLagEvent[] => {
  // 1) Normalize all inputs into UTC minutes or UTC datetimes.
  const originSleepStart = parseHHMM(inputs.originSleepStart)
  const originSleepEnd = parseHHMM(inputs.originSleepEnd)
  const destinationSleepStart = parseHHMM(inputs.destSleepStart)
  const destinationSleepEnd = parseHHMM(inputs.destSleepEnd)
  const travelStart = parseLocalDateTime(inputs.travelStart)
  const travelEnd = parseLocalDateTime(inputs.travelEnd)

  const originOffset = Number(inputs.originOffset)
  const destinationOffset = Number(inputs.destOffset)

  const originSleepStartUtc = sumTimeDelta(originSleepStart, -originOffset)
  const originSleepEndUtc = sumTimeDelta(originSleepEnd, -originOffset)
  const destinationSleepStartUtc = sumTimeDelta(destinationSleepStart, -destinationOffset)
  const destinationSleepEndUtc = sumTimeDelta(destinationSleepEnd, -destinationOffset)

  const travelStartUtc = addHours(travelStart, -originOffset)
  const travelEndUtc = addHours(travelEnd, -destinationOffset)
  if (travelEndUtc <= travelStartUtc) {
    throw new Error(`Travel end is before start: ${travelStartUtc.toISOString()}, ${travelEndUtc.toISOString()}`)
  }

  // 2) Determine when the calculation starts.
  const mode = (inputs.adjustmentStart || 'after_arrival').toLowerCase()
  const allowedAdjustmentModes = new Set([
    'after_arrival',
    'travel_start',
    'precondition',
    'precondition_with_travel',
  ])
  if (!allowedAdjustmentModes.has(mode)) {
    throw new Error(`invalid adjustment_start: ${inputs.adjustmentStart}`)
  }

  const preconditionDays = Math.max(Number(inputs.preDays || 0), 0)
  const effectivePreDays = mode === 'precondition' || mode === 'precondition_with_travel' ? preconditionDays : 0

  let startOfShift: Date
  if (mode === 'after_arrival') {
    startOfShift = travelEndUtc
  } else if (mode === 'travel_start') {
    startOfShift = travelStartUtc
  } else {
    startOfShift = addHours(addDays(midnightForDatetime(travelStart), -effectivePreDays), -originOffset)
  }

  // 3) Compute CBTmin at origin/destination and direction.
  const originCbtmin = sumTimeDelta(originSleepEndUtc, -3)
  const destCbtmin = sumTimeDelta(destinationSleepEndUtc, -3)
  const initialSignedDiff = signedDiffHours(destCbtmin, originCbtmin)
  const phaseDirection = initialSignedDiff > 0 ? 'delay' : initialSignedDiff < 0 ? 'advance' : 'aligned'
  const directionSign = phaseDirection === 'delay' ? 1 : -1

  const presets = PRESETS.default

  const optimalMelatoninOffset = phaseDirection === 'advance' ? presets.melatonin_advance : presets.melatonin_delay
  const optimalExerciseWindow = phaseDirection === 'advance' ? presets.exercise_advance : presets.exercise_delay
  const optimalLightWindow = phaseDirection === 'advance' ? presets.light_advance : presets.light_delay
  const optimalDarkWindow = phaseDirection === 'advance' ? presets.dark_advance : presets.dark_delay

  const noInterventionWindow =
    mode === 'travel_start' || mode === 'precondition_with_travel' ? null : ([travelStartUtc, travelEndUtc] as Interval)

  const buildInterventionSchedule = (lastCbtmin: Date): InterventionSchedule => {
    const melatoninAt = addHours(lastCbtmin, optimalMelatoninOffset + (phaseDirection === 'advance' ? 24 : 0))
    const exercise: Interval = [
      addHours(lastCbtmin, optimalExerciseWindow[0]),
      addHours(lastCbtmin, optimalExerciseWindow[1]),
    ]
    const light: Interval = [
      addHours(lastCbtmin, optimalLightWindow[0]),
      addHours(lastCbtmin, optimalLightWindow[1]),
    ]
    const dark: Interval = [
      addHours(lastCbtmin, optimalDarkWindow[0]),
      addHours(lastCbtmin, optimalDarkWindow[1]),
    ]

    return {
      melatonin: { enabled: false, at: melatoninAt },
      exercise: { enabled: false, window: exercise },
      light: { enabled: false, window: light },
      dark: { enabled: false, window: dark },
    }
  }

  const applyNoInterventionFilter = (schedule: InterventionSchedule, window: Interval | null) => {
    if (!window) return schedule
    return {
      melatonin: {
        ...schedule.melatonin,
        enabled: schedule.melatonin.enabled && !isInsideInterval(schedule.melatonin.at, window),
      },
      exercise: {
        ...schedule.exercise,
        enabled: schedule.exercise.enabled && intersectionHours(schedule.exercise.window, window) === 0,
      },
      light: {
        ...schedule.light,
        enabled: schedule.light.enabled && intersectionHours(schedule.light.window, window) === 0,
      },
      dark: {
        ...schedule.dark,
        enabled: schedule.dark.enabled && intersectionHours(schedule.dark.window, window) === 0,
      },
    }
  }

  const applySmallDiffRule = (schedule: InterventionSchedule, diffHours: number) => {
    if (Math.abs(diffHours) >= 3.0) return schedule
    return {
      melatonin: { ...schedule.melatonin, enabled: false },
      exercise: { ...schedule.exercise, enabled: false },
      light: { ...schedule.light, enabled: false },
      dark: { ...schedule.dark, enabled: false },
    }
  }

  const computeDelta = (
    schedule: InterventionSchedule,
    diffHours: number,
    precondition: boolean,
    nextCbtmin: Date,
  ) => {
    if (phaseDirection === 'aligned') return 0

    const anyIntervention =
      schedule.melatonin.enabled || schedule.exercise.enabled || schedule.light.enabled || schedule.dark.enabled

    let delta = anyIntervention ? (precondition ? 1.0 : 1.5) : precondition ? 0.0 : 1.0
    delta = Math.min(delta, Math.abs(diffHours))

    if (noInterventionWindow && intersectionHours([addHours(nextCbtmin, -8), nextCbtmin], noInterventionWindow) > 0) {
      delta = 0
    }

    return delta
  }

  const nextCbtTime = (cursor: Date, cbtMinutes: number) => {
    let next = combineDateMinutes(cursor, cbtMinutes)
    if (next <= cursor) next = addDays(next, 1)
    return next
  }

  // 4) Determine the first CBTmin.
  const numExtraBeforeDays = 2
  const numExtraAfterDays = 2
  const midnightStart = midnightForDatetime(addDays(travelStartUtc, -(effectivePreDays + numExtraBeforeDays)))

  const cbtEntries: CBTEntry[] = []
  let currentCbtMinutes = originCbtmin
  let timeCursor = nextCbtTime(midnightStart, currentCbtMinutes)

  cbtEntries.push({
    cbtmin: timeCursor,
    interventions: buildInterventionSchedule(addDays(timeCursor, -1)),
  })

  // 5) Iterate CBTmin shifts and schedule interventions until aligned.
  let extraDays = 0
  while (Math.abs(signedDiffHours(destCbtmin, currentCbtMinutes)) > EPSILON || extraDays < numExtraAfterDays) {
    if (Math.abs(signedDiffHours(destCbtmin, currentCbtMinutes)) <= EPSILON) {
      extraDays += 1
    }

    const isPrecondition =
      (mode === 'travel_start' || mode === 'precondition_with_travel') &&
      timeCursor > startOfShift &&
      timeCursor < travelStartUtc

    const nextCbt = nextCbtTime(timeCursor, currentCbtMinutes)
    let schedule = buildInterventionSchedule(addDays(nextCbt, -1))
    schedule = {
      melatonin: { ...schedule.melatonin, enabled: inputs.useMelatonin },
      exercise: { ...schedule.exercise, enabled: inputs.useExercise },
      light: { ...schedule.light, enabled: inputs.useLightDark },
      dark: { ...schedule.dark, enabled: inputs.useLightDark },
    }

    const diffHours = signedDiffHours(destCbtmin, currentCbtMinutes)
    schedule = applyNoInterventionFilter(schedule, noInterventionWindow)
    schedule = applySmallDiffRule(schedule, diffHours)

    let delta = computeDelta(schedule, diffHours, isPrecondition, nextCbt)
    if (timeCursor < startOfShift) delta = 0

    if (delta > 0) {
      currentCbtMinutes = sumTimeDelta(currentCbtMinutes, delta * directionSign)
    }

    const shiftedCbt = addHours(nextCbt, delta * directionSign)
    timeCursor = shiftedCbt

    cbtEntries.push({ cbtmin: shiftedCbt, interventions: schedule })
  }

  // Build sleep windows between calculation start and end.
  const midnightEnd = midnightForDatetime(addDays(cbtEntries[cbtEntries.length - 1].cbtmin, 1))
  const sleepWindows: Interval[] = []
  let sleepTime = midnightStart
  let sleepDest = false

  while (sleepTime < midnightEnd) {
    if (!sleepDest) {
      const [s, e] = nextInterval(sleepTime, [originSleepStartUtc, originSleepEndUtc], [
        travelStartUtc,
        travelEndUtc,
      ])
      if (!s || !e) {
        sleepTime = addDays(sleepTime, 1)
        continue
      }
      if (e > travelStartUtc || sleepDest) {
        const [sDest, eDest] = nextInterval(
          sleepTime,
          [destinationSleepStartUtc, destinationSleepEndUtc],
          [travelStartUtc, travelEndUtc],
        )
        sleepDest = true
        if (!sDest || !eDest) {
          sleepTime = addDays(sleepTime, 1)
          continue
        }
        sleepWindows.push([sDest, eDest])
        sleepTime = eDest
        continue
      }
      sleepWindows.push([s, e])
      sleepTime = e
      continue
    }

    const [s, e] = nextInterval(
      sleepTime,
      [destinationSleepStartUtc, destinationSleepEndUtc],
      [travelStartUtc, travelEndUtc],
    )
    if (!s || !e) {
      sleepTime = addDays(sleepTime, 1)
      continue
    }
    sleepWindows.push([s, e])
    sleepTime = e
  }

  // 6) Combine into a final events list.
  const events: JetLagEvent[] = []

  for (const [start, end] of sleepWindows) {
    events.push(
      buildEvent(
        'sleep',
        start,
        end,
        { is_sleep: true },
        { phase_direction: phaseDirection, signed_initial_diff_hours: initialSignedDiff },
      ),
    )
  }

  events.push(
    buildEvent(
      'travel',
      travelStartUtc,
      travelEndUtc,
      { is_travel: true },
      { phase_direction: phaseDirection, signed_initial_diff_hours: initialSignedDiff },
    ),
  )

  for (const entry of cbtEntries) {
    events.push(
      buildEvent(
        'cbtmin',
        entry.cbtmin,
        null,
        { is_cbtmin: true },
        { phase_direction: phaseDirection, signed_initial_diff_hours: initialSignedDiff },
      ),
    )

    if (entry.interventions.melatonin.enabled) {
      events.push(
        buildEvent(
          'melatonin',
          entry.interventions.melatonin.at,
          null,
          { is_melatonin: true },
          { phase_direction: phaseDirection, signed_initial_diff_hours: initialSignedDiff },
        ),
      )
    }

    if (entry.interventions.exercise.enabled) {
      for (const [start, end] of subtractIntervals(entry.interventions.exercise.window, sleepWindows)) {
        events.push(
          buildEvent(
            'exercise',
            start,
            end,
            { is_exercise: true },
            { phase_direction: phaseDirection, signed_initial_diff_hours: initialSignedDiff },
          ),
        )
      }
    }

    if (entry.interventions.light.enabled) {
      for (const [start, end] of subtractIntervals(entry.interventions.light.window, sleepWindows)) {
        events.push(
          buildEvent(
            'light',
            start,
            end,
            { is_light: true },
            { phase_direction: phaseDirection, signed_initial_diff_hours: initialSignedDiff },
          ),
        )
      }
    }

    if (entry.interventions.dark.enabled) {
      for (const [start, end] of subtractIntervals(entry.interventions.dark.window, sleepWindows)) {
        events.push(
          buildEvent(
            'dark',
            start,
            end,
            { is_dark: true },
            { phase_direction: phaseDirection, signed_initial_diff_hours: initialSignedDiff },
          ),
        )
      }
    }
  }

  events.sort((a, b) => a.start.localeCompare(b.start))
  return events
}
