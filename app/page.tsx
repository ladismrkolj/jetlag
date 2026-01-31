"use client"
import { useEffect, useMemo, useRef, useState } from 'react'
import styles from './page.module.css'
import ScheduleSvgGrid from './ScheduleSvgGrid'
import { createJetLagTimetable } from './lib/jetlag'
import TimezoneSelect from './components/TimezoneSelect'
import { getTimeZoneNames, getTimeZoneOffsetHours } from './lib/timezones'
import {
  Alert,
  Box,
  Button,
  ButtonBase,
  Card,
  CardContent,
  Checkbox,
  Chip,
  Container,
  CssBaseline,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  FormControlLabel,
  FormGroup,
  FormLabel,
  InputLabel,
  Link,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  ThemeProvider,
  Typography,
} from '@mui/material'
import { createTheme } from '@mui/material/styles'

type TzOffset = number // in hours, e.g. -5 for New York winter
type AdjustmentStartOption = 'after_arrival' | 'travel_start' | 'precondition' | 'precondition_with_travel'

type ShareSettings = {
  v: 1
  originTz: string
  destTz: string
  originSleepStart: string
  originSleepEnd: string
  destSleepStart: string
  destSleepEnd: string
  travelStart: string
  travelEnd: string
  melatonin: boolean
  lightDark: boolean
  exercise: boolean
  startAdjustments: AdjustmentStartOption
  preconditionDays: number
}

const OFFSET_MIN = -12
const OFFSET_MAX = 14
const OFFSET_STEP = 0.25
const SETTINGS_VERSION = 1
const TIME_PATTERN = /^(?:[01]\d|2[0-3]):[0-5]\d$/

const DEFAULT_ORIGIN_TZ = 'America/New_York'
const DEFAULT_DEST_TZ = 'Europe/Paris'
const SITE_URL = 'https://jetlag.lysiyo.com'

const ADJUSTMENT_OPTIONS: { value: AdjustmentStartOption; label: string }[] = [
  { value: 'after_arrival', label: 'After arrival' },
  { value: 'travel_start', label: 'At start of travel' },
  { value: 'precondition', label: 'Before travel (precondition days)' },
  { value: 'precondition_with_travel', label: 'Before travel (precondition days) incl. travel' },
]

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#111111' },
    secondary: { main: '#111111' },
    background: { default: '#ffffff', paper: '#ffffff' },
    text: { primary: '#111111', secondary: '#4b5563' },
  },
  shape: { borderRadius: 12 },
  typography: {
    fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji"',
    h1: { fontWeight: 700, letterSpacing: -0.3 },
    h2: { fontWeight: 600, letterSpacing: -0.2 },
    h3: { fontWeight: 600 },
    button: { fontWeight: 600, textTransform: 'none' },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        containedPrimary: {
          backgroundColor: '#111111',
          color: '#ffffff',
          boxShadow: 'none',
          '&:hover': { backgroundColor: '#1f2937', boxShadow: 'none' },
        },
        outlined: {
          borderColor: '#111111',
          color: '#111111',
          '&:hover': { borderColor: '#1f2937', backgroundColor: 'rgba(17, 17, 17, 0.04)' },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: { border: '1px solid #e5e7eb' },
      },
    },
    MuiLink: {
      styleOverrides: {
        root: { color: '#2563eb', textDecoration: 'underline', '&:hover': { textDecoration: 'none' } },
      },
    },
  },
})

export default function Page() {
  // Helpers
  const clamp = (n: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, n))
  const clampOffset = (value: number) => clamp(roundToQuarterHour(value), OFFSET_MIN, OFFSET_MAX)
  const fmtLocal = (d: Date) => {
    const pad = (x: number) => String(x).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
  }
  const noonPlusDays = (days: number) => {
    const d = new Date(); d.setDate(d.getDate() + days); d.setHours(12, 0, 0, 0); return fmtLocal(d)
  }
  const initialTravelStart = useMemo(() => noonPlusDays(1), [])
  const initialTravelEnd = useMemo(() => noonPlusDays(2), [])

  const [originOffset, setOriginOffset] = useState<TzOffset>(-5)
  const [destOffset, setDestOffset] = useState<TzOffset>(1)
  const [originTimeZone, setOriginTimeZone] = useState<string | null>(DEFAULT_ORIGIN_TZ)
  const [destTimeZone, setDestTimeZone] = useState<string | null>(DEFAULT_DEST_TZ)
  const [originSleepStart, setOriginSleepStart] = useState('23:00')
  const [originSleepEnd, setOriginSleepEnd] = useState('07:00')
  const [destSleepStart, setDestSleepStart] = useState('23:00')
  const [destSleepEnd, setDestSleepEnd] = useState('07:00')
  const [travelStart, setTravelStart] = useState(initialTravelStart) // tomorrow 12:00 local
  const [travelEnd, setTravelEnd] = useState(initialTravelEnd)     // day after 12:00 local
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
  const [betaEmail, setBetaEmail] = useState('')
  const [shareCopied, setShareCopied] = useState(false)

  const settingsReadyRef = useRef(false)
  const shareTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const defaultSettingsRef = useRef<ShareSettings>({
    v: SETTINGS_VERSION,
    originTz: DEFAULT_ORIGIN_TZ,
    destTz: DEFAULT_DEST_TZ,
    originSleepStart: '23:00',
    originSleepEnd: '07:00',
    destSleepStart: '23:00',
    destSleepEnd: '07:00',
    travelStart: initialTravelStart,
    travelEnd: initialTravelEnd,
    melatonin: true,
    lightDark: true,
    exercise: false,
    startAdjustments: 'after_arrival',
    preconditionDays: 2,
  })

  const shareSettings = useMemo<ShareSettings>(() => ({
    v: SETTINGS_VERSION,
    originTz: originTimeZone,
    destTz: destTimeZone,
    originSleepStart,
    originSleepEnd,
    destSleepStart,
    destSleepEnd,
    travelStart,
    travelEnd,
    melatonin: useMelatonin,
    lightDark: useLightDark,
    exercise: useExercise,
    startAdjustments: adjustmentStart,
    preconditionDays: preDays,
  }), [
    originTimeZone,
    destTimeZone,
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
  ])

  const originReferenceDate = useMemo(() => pickReferenceDate(travelStart), [travelStart])
  const destReferenceDate = useMemo(() => pickReferenceDate(travelEnd), [travelEnd])
  const [timezoneNames, setTimezoneNames] = useState<string[]>(() => getTimeZoneNames())
  const timezoneNameSet = useMemo(() => new Set(timezoneNames), [timezoneNames])

  useEffect(() => {
    // For beta: show on every reload for now
    setBetaOpen(true)
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    const encoded = params.get('s')
    if (!encoded) {
      settingsReadyRef.current = true
      return
    }
    const decoded = decodeSettingsParam(encoded)
    if (!decoded) {
      settingsReadyRef.current = true
      return
    }
    const tzNames = new Set(getAllTimeZoneNames())
    const sanitized = sanitizeSettings(decoded, defaultSettingsRef.current, tzNames)
    setOriginTimeZone(sanitized.originTz)
    setDestTimeZone(sanitized.destTz)
    setOriginSleepStart(sanitized.originSleepStart)
    setOriginSleepEnd(sanitized.originSleepEnd)
    setDestSleepStart(sanitized.destSleepStart)
    setDestSleepEnd(sanitized.destSleepEnd)
    setTravelStart(sanitized.travelStart)
    setTravelEnd(sanitized.travelEnd)
    setUseMelatonin(sanitized.melatonin)
    setUseLightDark(sanitized.lightDark)
    setUseExercise(sanitized.exercise)
    setAdjustmentStart(sanitized.startAdjustments)
    setPreDays(sanitized.preconditionDays)
    setPreDaysStr(String(sanitized.preconditionDays))
    settingsReadyRef.current = true
  }, [])

  useEffect(() => {
    // Refresh with the full Intl-provided list once we are on the client
    const names = getTimeZoneNames()
    if (!names.length) return
    setTimezoneNames(prev => {
      if (prev.length === names.length && prev.every((v, i) => v === names[i])) return prev
      return names
    })
  }, [])

  useEffect(() => {
    if (originTimeZone == null) return
    if (!timezoneNameSet.size) return
    if (!timezoneNameSet.has(originTimeZone)) {
      setOriginTimeZone(timezoneNames[0] ?? null)
    }
  }, [originTimeZone, timezoneNameSet, timezoneNames])

  useEffect(() => {
    if (destTimeZone == null) return
    if (!timezoneNameSet.size) return
    if (!timezoneNameSet.has(destTimeZone)) {
      setDestTimeZone(timezoneNames[0] ?? null)
    }
  }, [destTimeZone, timezoneNameSet, timezoneNames])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const storedOrigin = window.localStorage.getItem('jetlag.originTimeZone')
    const storedDest = window.localStorage.getItem('jetlag.destTimeZone')
    if (storedOrigin && timezoneNameSet.has(storedOrigin)) {
      setOriginTimeZone(storedOrigin)
    }
    if (storedDest && timezoneNameSet.has(storedDest)) {
      setDestTimeZone(storedDest)
    }
  }, [timezoneNameSet])

  useEffect(() => {
    if (typeof window === 'undefined') return
    if (originTimeZone) {
      window.localStorage.setItem('jetlag.originTimeZone', originTimeZone)
    } else {
      window.localStorage.removeItem('jetlag.originTimeZone')
    }
  }, [originTimeZone])

  useEffect(() => {
    if (typeof window === 'undefined') return
    if (destTimeZone) {
      window.localStorage.setItem('jetlag.destTimeZone', destTimeZone)
    } else {
      window.localStorage.removeItem('jetlag.destTimeZone')
    }
  }, [destTimeZone])

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

  useEffect(() => {
    if (!settingsReadyRef.current) return
    if (typeof window === 'undefined') return
    const nextUrl = buildShareUrl(window.location.href, shareSettings, defaultSettingsRef.current)
    if (!nextUrl) return
    window.history.replaceState(null, '', nextUrl)
  }, [shareSettings])

  useEffect(() => {
    return () => {
      if (shareTimeoutRef.current) {
        clearTimeout(shareTimeoutRef.current)
      }
    }
  }, [])

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const receivedEvents = createJetLagTimetable({
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

  const handleShare = async () => {
    if (typeof window === 'undefined') return
    const shareUrl = buildShareUrl(window.location.href, shareSettings, defaultSettingsRef.current)
    if (!shareUrl) return
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(shareUrl)
      } else {
        const textarea = document.createElement('textarea')
        textarea.value = shareUrl
        textarea.style.position = 'fixed'
        textarea.style.opacity = '0'
        document.body.appendChild(textarea)
        textarea.focus()
        textarea.select()
        document.execCommand('copy')
        document.body.removeChild(textarea)
      }
      setShareCopied(true)
      if (shareTimeoutRef.current) clearTimeout(shareTimeoutRef.current)
      shareTimeoutRef.current = setTimeout(() => setShareCopied(false), 2000)
    } catch (e) {
      console.warn('Failed to copy share link', e)
    }
  }

  // removed sample slots loader

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ minHeight: '100vh', background: '#ffffff', py: { xs: 3, md: 5 } }}>
        <Container maxWidth="lg">
          <Stack spacing={3}>
            <Paper
              className={styles.printBanner}
              elevation={0}
              sx={{
                background: '#ffffff',
                boxShadow: 'none',
              }}
            >
              <Box className={styles.printBannerText}>
                <Typography variant="h6" className={styles.printBannerTitle} sx={{ fontWeight: 700 }}>
                  Jet Lag Planner
                </Typography>
                <Typography variant="caption">jetlag.lysiyo.com</Typography>
                <Typography variant="caption">Scan to plan your next trip.</Typography>
              </Box>
              <Box
                component="img"
                className={styles.printBannerQr}
                src={`https://api.qrserver.com/v1/create-qr-code/?size=140x140&data=${encodeURIComponent(SITE_URL)}`}
                alt="QR code for jetlag.lysiyo.com"
                loading="lazy"
              />
            </Paper>

            <Button
              className={styles.bizLink}
              component="a"
              href="mailto:info@lysiyo.com?subject=Jet%20Lag%20Planner%20for%20Business"
              variant="contained"
              color="primary"
              sx={{
                alignSelf: 'flex-start',
                boxShadow: 'none',
                '&:hover': { boxShadow: 'none' },
              }}
            >
              <span className={styles.bizLabel}>Want to use this in your business? Contact us</span>
              <span className={styles.bizEmail}>info@lysiyo.com</span>
            </Button>

            <Paper
              component="form"
              className={styles.form}
              elevation={0}
              onSubmit={onSubmit}
              sx={{
                background: '#fafafa',
                boxShadow: 'none',
              }}
            >
              <Box className={styles.row}>
                <FormControl sx={{ minWidth: 240, flex: 1 }}>
                  <FormLabel>Origin time zone</FormLabel>
                  <TimezoneSelect
                    className={styles.timezoneSelect}
                    value={originTimeZone}
                    referenceDate={originReferenceDate}
                    onChange={next => setOriginTimeZone(next)}
                  />
                </FormControl>
                <FormControl sx={{ minWidth: 240, flex: 1 }}>
                  <FormLabel>Destination time zone</FormLabel>
                  <TimezoneSelect
                    className={styles.timezoneSelect}
                    value={destTimeZone}
                    referenceDate={destReferenceDate}
                    onChange={next => setDestTimeZone(next)}
                  />
                </FormControl>
              </Box>

              <Box className={styles.row}>
                <FormControl>
                  <FormLabel>Origin sleep</FormLabel>
                  <Stack direction="row" alignItems="center" spacing={1}>
                    <TextField
                      type="time"
                      value={originSleepStart}
                      onChange={e => setOriginSleepStart(e.target.value)}
                      size="small"
                      inputProps={{ step: 300, 'aria-label': 'Origin sleep start' }}
                    />
                    <Typography variant="body2" sx={{ opacity: 0.6 }}>→</Typography>
                    <TextField
                      type="time"
                      value={originSleepEnd}
                      onChange={e => setOriginSleepEnd(e.target.value)}
                      size="small"
                      inputProps={{ step: 300, 'aria-label': 'Origin sleep end' }}
                    />
                  </Stack>
                </FormControl>
                <FormControl>
                  <FormLabel>Destination sleep</FormLabel>
                  <Stack direction="row" alignItems="center" spacing={1}>
                    <TextField
                      type="time"
                      value={destSleepStart}
                      onChange={e => setDestSleepStart(e.target.value)}
                      size="small"
                      inputProps={{ step: 300, 'aria-label': 'Destination sleep start' }}
                    />
                    <Typography variant="body2" sx={{ opacity: 0.6 }}>→</Typography>
                    <TextField
                      type="time"
                      value={destSleepEnd}
                      onChange={e => setDestSleepEnd(e.target.value)}
                      size="small"
                      inputProps={{ step: 300, 'aria-label': 'Destination sleep end' }}
                    />
                  </Stack>
                </FormControl>
              </Box>

              <Box className={styles.row} sx={{ mt: 1.5 }}>
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                  <TextField
                    label="Travel start (origin local)"
                    type="datetime-local"
                    value={travelStart}
                    onChange={e => setTravelStart(e.target.value)}
                    size="small"
                    InputLabelProps={{ shrink: true }}
                  />
                  <TextField
                    label="Travel end (destination local)"
                    type="datetime-local"
                    value={travelEnd}
                    onChange={e => setTravelEnd(e.target.value)}
                    size="small"
                    InputLabelProps={{ shrink: true }}
                  />
                </Stack>
              </Box>

              <Box className={styles.row}>
                <FormGroup row>
                  <FormControlLabel
                    control={(
                      <Checkbox
                        checked={useMelatonin}
                        onChange={e => setUseMelatonin(e.target.checked)}
                      />
                    )}
                    label="Melatonin"
                  />
                  <FormControlLabel
                    control={(
                      <Checkbox
                        checked={useLightDark}
                        onChange={e => setUseLightDark(e.target.checked)}
                      />
                    )}
                    label="Light/Dark"
                  />
                  <FormControlLabel
                    control={(
                      <Checkbox
                        checked={useExercise}
                        onChange={e => setUseExercise(e.target.checked)}
                      />
                    )}
                    label="Exercise"
                  />
                </FormGroup>
                <FormControl size="small" sx={{ minWidth: 220 }}>
                  <InputLabel id="adjustmentStartLabel">Start adjustments</InputLabel>
                  <Select
                    labelId="adjustmentStartLabel"
                    id="adjustmentStart"
                    label="Start adjustments"
                    value={adjustmentStart}
                    onChange={e => setAdjustmentStart(e.target.value as AdjustmentStartOption)}
                  >
                    {ADJUSTMENT_OPTIONS.map(opt => (
                      <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <TextField
                  label="Precondition days"
                  id="preDaysInput"
                  type="number"
                  size="small"
                  inputProps={{ min: 0, max: 11, inputMode: 'numeric' }}
                  value={preDaysStr}
                  disabled={!['precondition', 'precondition_with_travel'].includes(adjustmentStart)}
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
              </Box>

              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} justifyContent="flex-end" className={styles.actions}>
                <Button type="submit" variant="contained" disabled={loading}>
                  {loading ? 'Calculating…' : 'Calculate'}
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => { if (typeof window !== 'undefined') window.print() }}
                >
                  Print this page
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => { setReportOpen(true); setReportMessage(null) }}
                >
                  Report a problem or suggestion
                </Button>
              </Stack>
            </Paper>

            {error && <Alert severity="error">{error}</Alert>}

            {events && (
              <Box className={styles.gridWrap}>
                <div className={styles.legend}>
                  <span className={styles.legendBox + ' ' + styles.sleep}>Sleep</span>
                  <span className={styles.legendBox + ' ' + styles.light}>Light</span>
                  <span className={styles.legendBox + ' ' + styles.dark}>Dark</span>
                  <span className={styles.legendBox + ' ' + styles.exercise}>Exercise</span>
                  <span className={styles.legendBox + ' ' + styles.melatonin}>Melatonin</span>
                  <span className={styles.legendBox + ' ' + styles.cbtmin}>CBTmin</span>
                  <span className={styles.legendBox + ' ' + styles.travel}>Travel</span>
                </div>
                <ScheduleSvgGrid days={groupEventsByUTCDate(events)} originOffset={legendOriginOffset} destOffset={legendDestOffset} />
              </Box>
            )}

            {events && (
              <Stack direction="row" spacing={2} justifyContent="center" alignItems="center" className={styles.emojiBand}>
                <ButtonBase
                  onClick={() => { setQuickRating('heart'); setQuickOpen(true); setQuickMessage(null) }}
                  aria-label="Love it"
                  sx={{ fontSize: 30, borderRadius: 999, px: 1.5, py: 1, transition: 'transform 0.08s ease', '&:hover': { transform: 'translateY(-1px) scale(1.05)' } }}
                >
                  ❤️
                </ButtonBase>
                <ButtonBase
                  onClick={() => { setQuickRating('party'); setQuickOpen(true); setQuickMessage(null) }}
                  aria-label="Great"
                  sx={{ fontSize: 30, borderRadius: 999, px: 1.5, py: 1, transition: 'transform 0.08s ease', '&:hover': { transform: 'translateY(-1px) scale(1.05)' } }}
                >
                  🎉
                </ButtonBase>
                <ButtonBase
                  onClick={() => { setQuickRating('down'); setQuickOpen(true); setQuickMessage(null) }}
                  aria-label="Not good"
                  sx={{ fontSize: 30, borderRadius: 999, px: 1.5, py: 1, transition: 'transform 0.08s ease', '&:hover': { transform: 'translateY(-1px) scale(1.05)' } }}
                >
                  👎
                </ButtonBase>
              </Stack>
            )}

            {events && (
              <Paper className={styles.tipsSection} elevation={0}>
                <Typography variant="h5" className={styles.tipsTitle}>
                  Quick Tips
                </Typography>
                <Box className={styles.tipGrid}>
                  <Card elevation={0} className={styles.tipCard}>
                    <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
                      <Typography variant="h6">Light Windows</Typography>
                      <Typography variant="body2">
                        When a slot says ideal for light, soak up brightness—get outside, sit near big windows, or use a light box if it’s dark. Stay in the light as long as it’s convenient.
                      </Typography>
                    </CardContent>
                  </Card>
                  <Card elevation={0} className={styles.tipCard}>
                    <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
                      <Typography variant="h6">Dark Windows</Typography>
                      <Typography variant="body2">
                        Ideal dark means cut light where you can. Close curtains, use a sleep mask, and if you’re awake wear dark or blue-blocking glasses (skip them when driving).
                      </Typography>
                    </CardContent>
                  </Card>
                  <Card elevation={0} className={styles.tipCard}>
                    <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
                      <Typography variant="h6">Sleep Windows</Typography>
                      <Typography variant="body2">
                        Ideal sleep windows flag great times to rest. On days without them, sleep when you need it—listen to your body.
                      </Typography>
                    </CardContent>
                  </Card>
                  <Card elevation={0} className={styles.tipCard}>
                    <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
                      <Typography variant="h6">Travel Reset</Typography>
                      <Box component="ul" sx={{ m: 0, pl: 2, fontSize: 13, color: 'text.secondary' }}>
                        <li>On the flight: drink plenty of water, reach for fruit.</li>
                        <li>After landing: hydrate, take a quick shower, and grab a 20-minute nap if you need it.</li>
                      </Box>
                    </CardContent>
                  </Card>
                </Box>
              </Paper>
            )}

            <Paper component="section" className={styles.explanation} elevation={0}>
              <Typography variant="h4" component="h2">Behind the Recommendation</Typography>

              <Typography variant="h6" component="h3">What the App Is Trying to Do</Typography>
              <Typography>
                Jet lag occurs when your internal circadian phase (the “body clock”) is out of sync with the new local time.
                The fastest way to reduce symptoms is to <strong>shift the clock</strong> efficiently while avoiding timing mistakes that push it the wrong way.
                Our scheduler uses three main levers:
              </Typography>
              <Box component="ul">
                <li><strong>Light</strong> (seek vs avoid)</li>
                <li><strong>Melatonin</strong> (dose and timing)</li>
                <li><strong>Exercise</strong> (being active)</li>
              </Box>
              <Typography>
                All timings are derived from peer-reviewed phase-response curves (PRCs) to light and melatonin,
                with practical rules distilled from&nbsp;
                <Link href="https://www.frontiersin.org/articles/10.3389/fphys.2019.00927/full" target="_blank" rel="noreferrer">Roach &amp; Sargent (2019)</Link><sup>[1]</sup>.
              </Typography>

              <Typography variant="h6" component="h3">Key Physiology (Why Timing Matters)</Typography>
              <Box component="ul">
                <li>
                  <strong>CBTmin (core body temperature minimum)</strong> is the circadian “pivot.”
                  Light in the ~12 h before CBTmin induces <strong>phase delays</strong>, while light in the ~12 h after CBTmin induces <strong>phase advances</strong>.
                  The largest shifts occur with light ~3–6 h either side of CBTmin&nbsp;
                  (<Link href="https://www.science.org/doi/10.1126/science.2734611" target="_blank" rel="noreferrer">Czeisler et al., 1989</Link><sup>[2]</sup>;
                  <Link href="https://physoc.onlinelibrary.wiley.com/doi/10.1113/jphysiol.2003.040477" target="_blank" rel="noreferrer">Khalsa et al., 2003</Link><sup>[3]</sup>).
                </li>
                <li>
                  <strong>Melatonin has its own PRC:</strong>
                  Maximum <strong>advances</strong> occur when taken ~11.5 h before CBTmin (~6.5 h before habitual bedtime);
                  maximum <strong>delays</strong> occur when taken ~4 h after CBTmin (~1 h after habitual wake).&nbsp;
                  (<Link href="https://doi.org/10.1113/jphysiol.2007.143180" target="_blank" rel="noreferrer">Burgess et al., 2008</Link><sup>[4]</sup>)
                </li>
              </Box>

              <Typography variant="h6" component="h3">How the App Generates Your Plan</Typography>
              <Box component="ol">
                <li><strong>Estimate starting phase:</strong> CBTmin is approximated as ~2–3 h before habitual wake time.</li>
                <li><strong>Compute target shift:</strong> Direction and magnitude of time zone change determine whether phase advances (eastward) or delays (westward) are scheduled.</li>
                <li>
                  <strong>Map PRCs to actions:</strong>
                  <Box component="ul">
                    <li><strong>Light:</strong> Seek bright light in the appropriate PRC zone (advance vs delay) and avoid it in the opposite zone.</li>
                    <li><strong>Melatonin (optional):</strong> Scheduled near the PRC peak for the desired shift direction, avoiding dead zones.</li>
                    <li><strong>Exercise (optional):</strong> Scheduled near the PRC peak, placed to reinforce the desired shift.</li>
                  </Box>
                </li>
                <li><strong>Apply constraints:</strong> Daily phase shifts are capped (~1–2 h/day), and travel demands are integrated.</li>
              </Box>

              <Typography variant="h6" component="h3">Why These Specific Timings Work</Typography>
              <Typography>
                <strong>Eastward travel:</strong> Morning light (post-CBTmin) plus evening melatonin accelerates advances and blocks delays.
                <br />
                <strong>Westward travel:</strong> Evening/night light (pre-CBTmin) plus morning light avoidance delay the clock efficiently. Melatonin may be used but is less critical.
              </Typography>

              <Typography variant="h6" component="h3">Risks and Side Effects</Typography>
              <Typography>
                <strong>Melatonin (3 mg immediate-release):</strong> Possible drowsiness, vivid dreams, headache, GI upset.
                May interact with anticoagulants, sedatives, antihypertensives, immunosuppressants. Not well studied in pregnancy, lactation, epilepsy, or autoimmune disease.
                Avoid activities requiring alertness if drowsy.
              </Typography>
              <Typography>
                <strong>Light:</strong> Nighttime light can impair sleep if mistimed.
              </Typography>
              <Typography>
                <strong>Sleep timing, naps, caffeine:</strong> Early-afternoon naps can reduce fatigue without harming night sleep. Caffeine aids alertness but does not shift the circadian phase.
              </Typography>

              <Typography variant="h6" component="h3">Limitations</Typography>
              <Box component="ul">
                <li>CBTmin is estimated, not measured—individual variation can cause mismatches.</li>
                <li>PRC data are averages; responses vary by genetics, age, light history, season.</li>
                <li>Light intensity and exposure vary in real-world conditions (clouds, indoor light).</li>
                <li>Flight schedules and commitments can constrain optimal timing.</li>
                <li>Evidence is based on specific melatonin doses/forms (3 mg immediate-release).</li>
                <li>Not a medical device—consult a clinician for medical conditions.</li>
              </Box>

              <Typography variant="h6" component="h3">Summary</Typography>
              <Typography>
                Your personalized schedule is built by estimating your circadian phase (CBTmin),
                calculating the advance or delay required, and aligning light, melatonin, exercise and sleep
                to the most effective PRC zones while avoiding exposure that would counteract the shift.
                The underlying science is drawn from laboratory circadian studies and expert synthesis.
                Outcomes will vary between individuals.
              </Typography>

              <Divider sx={{ my: 2 }} />

              <Typography variant="subtitle1" component="h4">References</Typography>
              <Box component="ol">
                <li>Roach GD, Sargent C. Interventions to Minimize Jet Lag After Westward and Eastward Flight. <em>Front Physiol</em>. 2019;10:927. <Link href="https://www.frontiersin.org/articles/10.3389/fphys.2019.00927/full" target="_blank" rel="noreferrer">Link</Link></li>
                <li>Czeisler CA, et al. Bright light induction of strong (type 0) resetting of the human circadian pacemaker. <em>Science</em>. 1989;244(4910):1328–1333. <Link href="https://www.science.org/doi/10.1126/science.2734611" target="_blank" rel="noreferrer">Link</Link></li>
                <li>Khalsa SB, et al. A phase response curve to single bright light pulses in human subjects. <em>J Physiol</em>. 2003;549(Pt 3):945–952. <Link href="https://physoc.onlinelibrary.wiley.com/doi/10.1113/jphysiol.2003.040477" target="_blank" rel="noreferrer">Link</Link></li>
                <li>Burgess HJ, et al. Human phase response curves to three days of daily melatonin: 0.5 mg versus 3.0 mg. <em>J Clin Endocrinol Metab</em>. 2008;93(12):4655–4660. <Link href="https://doi.org/10.1113/jphysiol.2007.143180" target="_blank" rel="noreferrer">Link</Link></li>
              </Box>
            </Paper>

            <Box component="footer" className={styles.siteFooter}>
              <Box className={styles.footerMeta}>
                <Typography variant="body2" className={styles.footerText}>
                  © {new Date().getFullYear()} Jet Lag Planner. Licensed under{' '}
                  <Link className={styles.footerLink} href="https://github.com/ladismrkolj/jetlag/blob/main/LICENSE" target="_blank" rel="noreferrer">
                    Business Source License 1.1
                  </Link>.
                </Typography>
                <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap" className={styles.footerShare}>
                  <Typography variant="body2" className={styles.footerLabel}>Share:</Typography>
                  <Link className={styles.footerLink} href={SITE_URL} target="_blank" rel="noreferrer">
                    {SITE_URL.replace('https://', '')}
                  </Link>
                </Stack>
                <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap" className={styles.footerShare}>
                  <Typography variant="body2" className={styles.footerLabel}>GitHub:</Typography>
                  <Link className={styles.footerLink} href="https://github.com/ladismrkolj/jetlag" target="_blank" rel="noreferrer">
                    ladismrkolj/jetlag
                  </Link>
                </Stack>
              </Box>
            </Box>
          </Stack>
        </Container>
      </Box>

      <Dialog open={reportOpen} onClose={() => !reportSending && setReportOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Send Feedback</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Optional: describe the issue or suggestion. We’ll include anonymous debug info.
          </Typography>
          <Stack spacing={2}>
            <TextField
              placeholder="Your message (optional)"
              multiline
              minRows={4}
              value={reportComment}
              onChange={e => setReportComment(e.target.value)}
            />
            <FormControlLabel
              control={(
                <Checkbox
                  checked={includeScreenshot}
                  onChange={e => setIncludeScreenshot(e.target.checked)}
                />
              )}
              label="Include page screenshot"
            />
            <TextField
              placeholder="Email for updates (optional)"
              value={reportEmail}
              onChange={e => setReportEmail(e.target.value)}
            />
            {reportMessage && (
              <Alert severity={reportMessage.startsWith('Thanks') ? 'success' : 'warning'}>
                {reportMessage}
              </Alert>
            )}
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            variant="contained"
            disabled={reportSending}
            onClick={async () => {
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
            }}
          >
            {reportSending ? 'Sending…' : ((reportEmail || '').trim() ? 'Send & Subscribe' : 'Send')}
          </Button>
          <Button variant="outlined" onClick={() => setReportOpen(false)} disabled={reportSending}>Close</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={betaOpen} onClose={() => setBetaOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Beta Notice</DialogTitle>
        <DialogContent>
          <Stack spacing={2}>
            <Typography variant="body2" color="text.secondary">
              This tool is in beta. Results are experimental and should not be used for medical decisions.
            </Typography>
            <Typography variant="body2" color="text.secondary">
              After you try the tool, you can share feedback or suggest a name using the feedback button.
            </Typography>
            <TextField
              placeholder="Email for updates (optional)"
              value={betaEmail}
              onChange={e => setBetaEmail(e.target.value)}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            variant="contained"
            onClick={async () => {
              const email = (betaEmail || '').trim()
              if (email) {
                try {
                  await fetch('/api/report', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ type: 'subscribe', email, source: 'beta_modal', url: typeof location !== 'undefined' ? location.href : 'unknown' }),
                  })
                } catch {}
              }
              setBetaOpen(false)
            }}
          >
            {(betaEmail || '').trim() ? 'I understand & Subscribe' : 'I understand'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={quickOpen} onClose={() => !quickSending && setQuickOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Quick Feedback</DialogTitle>
        <DialogContent>
          <Stack spacing={2}>
            <Typography variant="body2" color="text.secondary">
              How did it go? Your selected reaction: {quickRating === 'heart' ? '❤️ Love it' : quickRating === 'party' ? '🎉 Great' : '👎 Not good'}
            </Typography>
            <TextField
              placeholder="What worked? What didn’t? (optional)"
              multiline
              minRows={3}
              value={quickComment}
              onChange={e => setQuickComment(e.target.value)}
            />
            <TextField
              placeholder="Suggest a name for the site (optional)"
              value={quickName}
              onChange={e => setQuickName(e.target.value)}
            />
            <TextField
              placeholder="Email for updates (optional)"
              value={quickEmail}
              onChange={e => setQuickEmail(e.target.value)}
            />
            {quickMessage && (
              <Alert severity={quickMessage.startsWith('Thanks') ? 'success' : 'warning'}>
                {quickMessage}
              </Alert>
            )}
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            variant="contained"
            disabled={quickSending}
            onClick={async () => {
              setQuickSending(true); setQuickMessage(null)
              try {
                const payload: any = {
                  type: 'quick_feedback',
                  rating: quickRating,
                  comment: quickComment || null,
                  nameSuggestion: quickName || null,
                  email: (quickEmail || '').trim() || null,
                  inputs: { originOffset, destOffset, preDays, adjustmentStart },
                  url: typeof location !== 'undefined' ? location.href : 'unknown',
                }
                const res = await fetch('/api/report', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
                const body = await res.json().catch(() => ({}))
                if (!res.ok) throw new Error(body.error || `HTTP ${res.status}`)
                setQuickMessage('Thanks for the feedback!')
                setQuickName(''); setQuickComment(''); setQuickEmail('')
              } catch (e: any) {
                setQuickMessage(e?.message || 'Failed to send')
              } finally {
                setQuickSending(false)
              }
            }}
          >
            {quickSending ? 'Sending…' : ((quickEmail || '').trim() ? 'Send & Subscribe' : 'Send')}
          </Button>
          <Button variant="outlined" onClick={() => setQuickOpen(false)} disabled={quickSending}>Close</Button>
        </DialogActions>
      </Dialog>
    </ThemeProvider>
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
      let sleepCoversSlot = false
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
          if (e.is_sleep && es && ee && es <= slotStart && ee >= slotEnd) {
            sleepCoversSlot = true
          }
        }
      }
      if (sleepCoversSlot) {
        flags.is_light = false
        flags.is_dark = false
        flags.is_exercise = false
      }
      slots.push({ ...flags, start: slotStart.toISOString(), end: slotEnd.toISOString() })
    }
    days.push({ date: dateStr, slots })
  }
  return days
}

function roundToQuarterHour(value: number): number {
  return Math.round(value * 4) / 4
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

function formatDateTimeLocal(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function noonPlusDays(days: number): string {
  const date = new Date()
  date.setDate(date.getDate() + days)
  date.setHours(12, 0, 0, 0)
  return formatDateTimeLocal(date)
}

function base64UrlEncode(input: string): string {
  const bytes = new TextEncoder().encode(input)
  let binary = ''
  bytes.forEach(byte => {
    binary += String.fromCharCode(byte)
  })
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
}

function base64UrlDecode(input: string): string | null {
  const normalized = input.replace(/-/g, '+').replace(/_/g, '/')
  const padded = normalized + '==='.slice((normalized.length + 3) % 4)
  try {
    const binary = atob(padded)
    const bytes = Uint8Array.from(binary, char => char.charCodeAt(0))
    return new TextDecoder().decode(bytes)
  } catch {
    return null
  }
}

function encodeSettings(settings: ShareSettings): string | null {
  try {
    return base64UrlEncode(JSON.stringify(settings))
  } catch {
    return null
  }
}

function decodeSettingsParam(param: string): unknown | null {
  const decoded = base64UrlDecode(param)
  if (!decoded) return null
  try {
    return JSON.parse(decoded)
  } catch {
    return null
  }
}

function coerceBoolean(value: unknown): boolean | null {
  if (value === true || value === false) return value
  if (value === 1 || value === '1') return true
  if (value === 0 || value === '0') return false
  return null
}

function coerceDateTimeLocal(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return null
  return formatDateTimeLocal(parsed)
}

function sanitizeSettings(raw: unknown, defaults: ShareSettings, tzNames: Set<string>): ShareSettings {
  if (!raw || typeof raw !== 'object') return defaults
  const candidate = raw as Record<string, unknown>
  if (candidate.v !== SETTINGS_VERSION) return defaults
  const sanitized: ShareSettings = { ...defaults }
  if (typeof candidate.originTz === 'string' && tzNames.has(candidate.originTz)) {
    sanitized.originTz = candidate.originTz
  }
  if (typeof candidate.destTz === 'string' && tzNames.has(candidate.destTz)) {
    sanitized.destTz = candidate.destTz
  }
  if (typeof candidate.originSleepStart === 'string' && TIME_PATTERN.test(candidate.originSleepStart)) {
    sanitized.originSleepStart = candidate.originSleepStart
  }
  if (typeof candidate.originSleepEnd === 'string' && TIME_PATTERN.test(candidate.originSleepEnd)) {
    sanitized.originSleepEnd = candidate.originSleepEnd
  }
  if (typeof candidate.destSleepStart === 'string' && TIME_PATTERN.test(candidate.destSleepStart)) {
    sanitized.destSleepStart = candidate.destSleepStart
  }
  if (typeof candidate.destSleepEnd === 'string' && TIME_PATTERN.test(candidate.destSleepEnd)) {
    sanitized.destSleepEnd = candidate.destSleepEnd
  }
  const travelStart = coerceDateTimeLocal(candidate.travelStart)
  if (travelStart) sanitized.travelStart = travelStart
  const travelEnd = coerceDateTimeLocal(candidate.travelEnd)
  if (travelEnd) sanitized.travelEnd = travelEnd
  const melatonin = coerceBoolean(candidate.melatonin)
  if (melatonin != null) sanitized.melatonin = melatonin
  const lightDark = coerceBoolean(candidate.lightDark)
  if (lightDark != null) sanitized.lightDark = lightDark
  const exercise = coerceBoolean(candidate.exercise)
  if (exercise != null) sanitized.exercise = exercise
  if (typeof candidate.startAdjustments === 'string' && ADJUSTMENT_OPTIONS.some(opt => opt.value === candidate.startAdjustments)) {
    sanitized.startAdjustments = candidate.startAdjustments as AdjustmentStartOption
  }
  if (typeof candidate.preconditionDays === 'number' || typeof candidate.preconditionDays === 'string') {
    const parsed = Number(candidate.preconditionDays)
    if (Number.isFinite(parsed) && parsed >= 0) {
      sanitized.preconditionDays = Math.floor(parsed)
    }
  }
  return sanitized
}

function areSettingsEqual(a: ShareSettings, b: ShareSettings): boolean {
  return JSON.stringify(a) === JSON.stringify(b)
}

function buildShareUrl(currentUrl: string, settings: ShareSettings, defaults: ShareSettings): string | null {
  try {
    const url = new URL(currentUrl)
    if (areSettingsEqual(settings, defaults)) {
      url.searchParams.delete('s')
      return url.toString()
    }
    const encoded = encodeSettings(settings)
    if (!encoded) return null
    url.searchParams.set('s', encoded)
    return url.toString()
  } catch {
    return null
  }
}
