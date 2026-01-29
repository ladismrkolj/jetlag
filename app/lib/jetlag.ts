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

type InterventionTuple = [
  [boolean, Date],
  [boolean, [Date, Date]],
  [boolean, [Date, Date]],
  [boolean, [Date, Date]]
]

type CBTEntry = [Date, InterventionTuple]

const PRESETS = {
  default: {
    melatonin_advance: -11.5,
    melatonin_delay: 4,
    exercise_advance: [0, 3] as [number, number],
    exercise_delay: [-3, 0] as [number, number],
    light_advance: [0, 3] as [number, number],
    light_delay: [-3, 0] as [number, number],
    dark_advance: [-3, 0] as [number, number],
    dark_delay: [0, 3] as [number, number],
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

const subtractTimes = (timeMinutes1: number, timeMinutes2: number) => timeMinutes1 - timeMinutes2

const hoursFromMinutes = (minutes: number) => minutes / 60

const intersectionHours = (interval1: Interval, interval2: Interval) => {
  const [start1, end1] = interval1
  const [start2, end2] = interval2
  const latestStart = Math.max(start1.getTime(), start2.getTime())
  const earliestEnd = Math.min(end1.getTime(), end2.getTime())
  if (latestStart >= earliestEnd) return 0
  return (earliestEnd - latestStart) / MS_HOUR
}

const isInsideInterval = (ts: Date, interval: Interval) => ts >= interval[0] && ts < interval[1]

const midnightForDatetime = (dt: Date) =>
  new Date(Date.UTC(dt.getUTCFullYear(), dt.getUTCMonth(), dt.getUTCDate(), 0, 0, 0, 0))

const toIso = (dt: Date) => dt.toISOString().replace('.000Z', 'Z')

const combineDateMinutes = (date: Date, minutesFromMidnight: number) => {
  const midnight = Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate(), 0, 0, 0, 0)
  return new Date(midnight + minutesFromMidnight * MS_MINUTE)
}

const nextInterval = (
  time: Date,
  interval: [number, number],
  filterWindow: Interval | null = null,
): [Date | null, Date | null] => {
  const [startTimeMinutes, endTimeMinutes] = interval
  const refDate = time
  let startDt = combineDateMinutes(refDate, startTimeMinutes)
  let endDt = combineDateMinutes(refDate, endTimeMinutes)

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

  if (filterWindow && intersectionHours([startDt, endDt], filterWindow) > 0) {
    return [null, null]
  }

  return [startDt, endDt]
}

class CBTmin {
  originCbtmin: number
  destCbtmin: number
  presets: typeof PRESETS.default
  cbtmin: number
  phase_direction: string

  constructor(originCbtmin: number, destCbtmin: number, shiftPreset = 'default') {
    this.originCbtmin = originCbtmin
    this.destCbtmin = destCbtmin
    this.presets = PRESETS[shiftPreset as keyof typeof PRESETS] ?? PRESETS.default
    this.cbtmin = originCbtmin
    const diff = this.signedDifference()
    this.phase_direction = diff > 0 ? 'delay' : diff < 0 ? 'advance' : 'aligned'
  }

  signedDifference() {
    const diff = hoursFromMinutes(subtractTimes(this.destCbtmin, this.cbtmin))
    let norm = mod(diff + 12, 24) - 12
    if (norm === -12) norm = 12
    return norm
  }

  deltaCbtmin(melatonin: boolean, exercise: boolean, lightDark: boolean, precondition: boolean) {
    if (melatonin || exercise || lightDark) {
      if (Math.abs(this.signedDifference()) > 3.0) {
        return precondition ? 1.0 : 1.5
      }
      return precondition ? 1.0 : 1.5
    }
    if (Math.abs(this.signedDifference()) > 3.0) {
      return precondition ? 0.0 : 1.0
    }
    return precondition ? 0.0 : 1.0
  }

  static fromSleep(
    originSleepStart: number,
    originSleepEnd: number,
    destSleepStart: number,
    destSleepEnd: number,
    shiftPreset = 'default',
  ) {
    const originCbtmin = sumTimeDelta(originSleepEnd, -3)
    const destCbtmin = sumTimeDelta(destSleepEnd, -3)
    return new CBTmin(originCbtmin, destCbtmin, shiftPreset)
  }

  optimalMelatoninTime() {
    return this.phase_direction === 'advance'
      ? this.presets.melatonin_advance
      : this.presets.melatonin_delay
  }

  optimalExerciseWindow() {
    return this.phase_direction === 'advance'
      ? this.presets.exercise_advance
      : this.presets.exercise_delay
  }

  optimalLightWindow() {
    return this.phase_direction === 'advance'
      ? this.presets.light_advance
      : this.presets.light_delay
  }

  optimalDarkWindow() {
    return this.phase_direction === 'advance'
      ? this.presets.dark_advance
      : this.presets.dark_delay
  }

  nextCbtmin(
    time: Date,
    options: {
      noInterventionWindow?: Interval | null
      melatonin?: boolean
      exercise?: boolean
      light?: boolean
      dark?: boolean
      precondition?: boolean
      skipShift?: boolean
    } = {},
  ): CBTEntry {
    const {
      noInterventionWindow = null,
      melatonin = true,
      exercise = true,
      light = true,
      dark = true,
      precondition = true,
      skipShift = false,
    } = options

    let nextCbtmin = combineDateMinutes(time, this.cbtmin)
    if (nextCbtmin <= time) {
      nextCbtmin = addDays(nextCbtmin, 1)
    }
    const lastCbtmin = addDays(nextCbtmin, -1)

    const optimalMelatonin = addHours(
      lastCbtmin,
      this.optimalMelatoninTime() + (this.phase_direction === 'advance' ? 24 : 0),
    )
    const exerciseWindow = this.optimalExerciseWindow()
    const optimalExercise: [Date, Date] = [
      addHours(lastCbtmin, exerciseWindow[0]),
      addHours(lastCbtmin, exerciseWindow[1]),
    ]
    const lightWindow = this.optimalLightWindow()
    const optimalLight: [Date, Date] = [
      addHours(lastCbtmin, lightWindow[0]),
      addHours(lastCbtmin, lightWindow[1]),
    ]
    const darkWindow = this.optimalDarkWindow()
    const optimalDark: [Date, Date] = [
      addHours(lastCbtmin, darkWindow[0]),
      addHours(lastCbtmin, darkWindow[1]),
    ]

    const window = noInterventionWindow
    const usedMelatonin = window && isInsideInterval(optimalMelatonin, window) ? false : melatonin
    const usedExercise = window && intersectionHours(optimalExercise, window) > 0 ? false : exercise
    const usedLight = window && intersectionHours(optimalLight, window) > 0 ? false : light
    const usedDark = window && intersectionHours(optimalDark, window) > 0 ? false : dark

    let effectiveLight = usedLight
    let effectiveDark = usedDark
    let effectiveMelatonin = usedMelatonin
    let effectiveExercise = usedExercise

    if (Math.abs(this.signedDifference()) < 3.0) {
      effectiveLight = false
      effectiveDark = false
      effectiveMelatonin = false
      effectiveExercise = false
    }

    let cbtminDelta = Math.max(
      this.deltaCbtmin(effectiveMelatonin, effectiveExercise, effectiveLight || effectiveDark, precondition),
      0,
    )

    if (cbtminDelta > Math.abs(this.signedDifference())) {
      cbtminDelta = Math.abs(this.signedDifference())
    }

    if (
      window &&
      intersectionHours([addHours(nextCbtmin, -8), nextCbtmin], window) > 0
    ) {
      cbtminDelta = 0
    }

    if (cbtminDelta === 0 || this.phase_direction === 'aligned' || skipShift) {
      return [
        nextCbtmin,
        [
          [false, optimalMelatonin],
          [false, optimalExercise],
          [false, optimalLight],
          [false, optimalDark],
        ],
      ]
    }

    const directionSign = this.phase_direction === 'delay' ? 1 : -1
    this.cbtmin = sumTimeDelta(this.cbtmin, cbtminDelta * directionSign)
    nextCbtmin = addHours(nextCbtmin, cbtminDelta * directionSign)

    const interventions: InterventionTuple = [
      [effectiveMelatonin, optimalMelatonin],
      [effectiveExercise, optimalExercise],
      [effectiveLight, optimalLight],
      [effectiveDark, optimalDark],
    ]

    return [nextCbtmin, interventions]
  }
}

export const createJetLagTimetable = (inputs: JetLagInputs): JetLagEvent[] => {
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

  const cbt = CBTmin.fromSleep(
    originSleepStartUtc,
    originSleepEndUtc,
    destinationSleepStartUtc,
    destinationSleepEndUtc,
    'default',
  )

  const numExtraBeforeDays = 2
  const numExtraAfterDays = 2

  const midnightStartOfCalculations = midnightForDatetime(
    addDays(travelStartUtc, -(effectivePreDays + numExtraBeforeDays)),
  )

  const cbtEntries: CBTEntry[] = []
  const noInterventionWindow =
    mode === 'travel_start' || mode === 'precondition_with_travel'
      ? null
      : ([travelStartUtc, travelEndUtc] as Interval)

  const [firstCbtmin] = cbt.nextCbtmin(midnightStartOfCalculations, {
    noInterventionWindow,
    melatonin: inputs.useMelatonin,
    exercise: inputs.useExercise,
    light: inputs.useLightDark,
    dark: inputs.useLightDark,
    precondition: false,
    skipShift: true,
  })

  cbtEntries.push([
    firstCbtmin,
    [
      [false, firstCbtmin],
      [false, [firstCbtmin, firstCbtmin]],
      [false, [firstCbtmin, firstCbtmin]],
      [false, [firstCbtmin, firstCbtmin]],
    ],
  ])

  let timeCursor = firstCbtmin
  let extraDays = 0
  while (Math.abs(cbt.signedDifference()) > EPSILON || extraDays < numExtraAfterDays) {
    if (Math.abs(cbt.signedDifference()) < EPSILON) {
      extraDays += 1
    }

    const isPrecondition =
      (mode === 'travel_start' || mode === 'precondition_with_travel') &&
      timeCursor > startOfShift &&
      timeCursor < travelStartUtc

    const [nextCbt, interventions] = cbt.nextCbtmin(timeCursor, {
      noInterventionWindow,
      melatonin: inputs.useMelatonin,
      exercise: inputs.useExercise,
      light: inputs.useLightDark,
      dark: inputs.useLightDark,
      precondition: isPrecondition,
      skipShift: timeCursor < startOfShift,
    })

    cbtEntries.push([nextCbt, interventions])
    timeCursor = nextCbt
  }

  const midnightEndOfCalculations = midnightForDatetime(addDays(cbtEntries[cbtEntries.length - 1][0], 1))

  const interventionEvents: JetLagEvent[] = []

  const signedDiff = cbt.signedDifference()
  const phaseDirection = cbt.phase_direction

  for (const entry of cbtEntries) {
    const [cbtTime, interventions] = entry
    interventionEvents.push({
      event: 'cbtmin',
      start: toIso(cbtTime),
      end: null,
      is_cbtmin: true,
      is_melatonin: false,
      is_light: false,
      is_dark: false,
      is_exercise: false,
      is_sleep: false,
      is_travel: false,
      day_index: null,
      phase_direction: phaseDirection,
      signed_initial_diff_hours: signedDiff,
    })

    if (interventions[0][0]) {
      interventionEvents.push({
        event: 'melatonin',
        start: toIso(interventions[0][1]),
        end: null,
        is_cbtmin: false,
        is_melatonin: true,
        is_light: false,
        is_dark: false,
        is_exercise: false,
        is_sleep: false,
        is_travel: false,
        day_index: null,
        phase_direction: phaseDirection,
        signed_initial_diff_hours: signedDiff,
      })
    }

    if (interventions[1][0]) {
      interventionEvents.push({
        event: 'exercise',
        start: toIso(interventions[1][1][0]),
        end: toIso(interventions[1][1][1]),
        is_cbtmin: false,
        is_melatonin: false,
        is_light: false,
        is_dark: false,
        is_exercise: true,
        is_sleep: false,
        is_travel: false,
        day_index: null,
        phase_direction: phaseDirection,
        signed_initial_diff_hours: signedDiff,
      })
    }

    if (interventions[2][0]) {
      interventionEvents.push({
        event: 'light',
        start: toIso(interventions[2][1][0]),
        end: toIso(interventions[2][1][1]),
        is_cbtmin: false,
        is_melatonin: false,
        is_light: true,
        is_dark: false,
        is_exercise: false,
        is_sleep: false,
        is_travel: false,
        day_index: null,
        phase_direction: phaseDirection,
        signed_initial_diff_hours: signedDiff,
      })
    }

    if (interventions[3][0]) {
      interventionEvents.push({
        event: 'dark',
        start: toIso(interventions[3][1][0]),
        end: toIso(interventions[3][1][1]),
        is_cbtmin: false,
        is_melatonin: false,
        is_light: false,
        is_dark: true,
        is_exercise: false,
        is_sleep: false,
        is_travel: false,
        day_index: null,
        phase_direction: phaseDirection,
        signed_initial_diff_hours: signedDiff,
      })
    }
  }

  const sleepWindows: Interval[] = []
  let sleepTime = midnightStartOfCalculations
  let sleepDest = false

  while (sleepTime < midnightEndOfCalculations) {
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

  const events: JetLagEvent[] = []

  for (const [start, end] of sleepWindows) {
    events.push({
      event: 'sleep',
      start: toIso(start),
      end: toIso(end),
      is_cbtmin: false,
      is_melatonin: false,
      is_light: false,
      is_dark: false,
      is_exercise: false,
      is_sleep: true,
      is_travel: false,
      day_index: null,
      phase_direction: phaseDirection,
      signed_initial_diff_hours: signedDiff,
    })
  }

  events.push({
    event: 'travel',
    start: toIso(travelStartUtc),
    end: toIso(travelEndUtc),
    is_cbtmin: false,
    is_melatonin: false,
    is_light: false,
    is_dark: false,
    is_exercise: false,
    is_sleep: false,
    is_travel: true,
    day_index: null,
    phase_direction: phaseDirection,
    signed_initial_diff_hours: signedDiff,
  })

  events.push(...interventionEvents)

  events.sort((a, b) => a.start.localeCompare(b.start))
  return events
}
