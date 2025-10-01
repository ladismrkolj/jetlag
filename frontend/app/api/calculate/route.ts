import { NextRequest, NextResponse } from 'next/server'
import { spawn } from 'child_process'
import fs from 'fs'
import path from 'path'
import { google } from 'googleapis'

type Inputs = {
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
  adjustmentStart: 'after_arrival' | 'travel_start' | 'precondition'
}

export async function POST(req: NextRequest) {
  const body = (await req.json()) as Inputs
  try {
    if (process.env.CALC_DEBUG) {
    const dbgIn = JSON.stringify(body)
      console.log(`[calculate] input ${dbgIn.length} bytes`, dbgIn.slice(0, 1000))
    }
    const t0 = Date.now()
    const events = await runPythonTimetable(body)
    const dt = Date.now() - t0
    // Log asynchronously after response so UI isn't delayed by Sheets write
    setTimeout(() => {
      appendCalculationLog(req, body, { eventsCount: events?.length ?? 0, durationMs: dt }).catch((e) => {
        if (process.env.CALC_DEBUG) console.warn('[calculate] log error', e)
      })
    }, 0)
    if (process.env.CALC_DEBUG) {
      console.log(`[calculate] returned ${Array.isArray(events)?events.length:'n/a'} events in ${dt}ms`)
    }
    return NextResponse.json({ events })
  } catch (e: any) {
    const msg = e?.message ?? 'Error'
    if (process.env.CALC_DEBUG) console.error('[calculate] error:', msg)
    // In debug, attach message; in prod keep minimal
    const bodyOut: any = process.env.CALC_DEBUG ? { error: msg } : { error: 'Error' }
    return NextResponse.json(bodyOut, { status: 400 })
  }
}

function runPythonTimetable(inp: Inputs): Promise<any[]> {
  return new Promise((resolve, reject) => {
    // Determine repo root so Python can import the package at top-level
    const cwd = process.cwd()
    const hasHere = fs.existsSync(path.join(cwd, 'jetlag_core', 'cli.py'))
    const parent = path.resolve(cwd, '..')
    const repoRoot = hasHere ? cwd : (fs.existsSync(path.join(parent, 'jetlag_core', 'cli.py')) ? parent : cwd)

    const trySpawn = (cmd: string) => spawn(cmd, ['-u', '-m', 'jetlag_core.cli'], { cwd: repoRoot, env: { ...process.env } })
    let proc = trySpawn('python3')
    let triedFallback = false
    let out = ''
    let err = ''
    const attach = () => {
      proc.stdout.on('data', (d) => { out += d.toString() })
      proc.stderr.on('data', (d) => { err += d.toString() })
      proc.on('error', (e: any) => {
        if (!triedFallback) {
          triedFallback = true
          proc = trySpawn('python')
          attach()
          proc.stdin.write(JSON.stringify(inp))
          proc.stdin.end()
        } else {
          if (process.env.CALC_DEBUG) console.error('[calculate] spawn error:', e)
          reject(e)
        }
      })
      proc.on('close', (code) => {
        if (process.env.CALC_DEBUG) {
          if (err) console.warn(`[calculate] python stderr (${err.length} bytes):\n${err.slice(0, 1024)}`)
          if (out) console.log(`[calculate] python stdout (${out.length} bytes):\n${out.slice(0, 1024)}`)
        }
        if (code !== 0) {
          try {
            const parsed = JSON.parse(out || '{}')
            reject(new Error(parsed.error || err || `python exited ${code}`))
          } catch {
            reject(new Error(err || `python exited ${code}`))
          }
          return
        }
        try {
          const parsed = JSON.parse(out)
          if (parsed && Array.isArray(parsed.events)) return resolve(parsed.events)
          return reject(new Error('invalid response from python'))
        } catch (e: any) {
          return reject(new Error(`parse error: ${e?.message || 'unknown'}`))
        }
      })
    }
    attach()
    proc.stdin.write(JSON.stringify(inp))
    proc.stdin.end()
  })
}

// Ensure Node runtime (needed to spawn child processes)
export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

async function appendCalculationLog(req: NextRequest, inputs: Inputs, stats: { eventsCount: number; durationMs: number }) {
  const sheetId = process.env.GOOGLE_CALC_SHEETS_ID || process.env.GOOGLE_SHEETS_ID
  const sheetTab = process.env.GOOGLE_CALC_SHEETS_TAB || 'Calculations'
  const clientEmail = process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL
  const privateKeyRaw = process.env.GOOGLE_PRIVATE_KEY
  if (!sheetId || !clientEmail || !privateKeyRaw) return

  const privateKey = privateKeyRaw.replace(/\\n/g, '\n')
  const auth = new google.auth.JWT({
    email: clientEmail,
    key: privateKey,
    scopes: ['https://www.googleapis.com/auth/spreadsheets'],
  })
  const sheets = google.sheets({ version: 'v4', auth })

  const now = new Date().toISOString()
  const rawForwardedFor = req.headers.get('x-forwarded-for') || ''
  const externalIp = req.headers.get('x-real-ip') || rawForwardedFor.split(',')[0]?.trim() || ''
  const ua = req.headers.get('user-agent') || ''
  const referer = req.headers.get('referer') || ''
  const country = req.headers.get('x-vercel-ip-country') || ''
  const region = req.headers.get('x-vercel-ip-country-region') || ''
  const city = req.headers.get('x-vercel-ip-city') || ''

  const bool = (value: boolean) => (value ? 'Y' : 'N')

  const values = [[
    now,
    inputs.originOffset,
    inputs.destOffset,
    inputs.preDays,
    inputs.travelStart,
    inputs.travelEnd,
    bool(inputs.useMelatonin),
    bool(inputs.useLightDark),
    bool(inputs.useExercise),
    inputs.adjustmentStart,
    stats.eventsCount,
    stats.durationMs,
    ua,
    externalIp,
    rawForwardedFor,
    country,
    region,
    city,
    referer,
  ]]

  await sheets.spreadsheets.values.append({
    spreadsheetId: sheetId,
    range: `${sheetTab}!A1`,
    valueInputOption: 'RAW',
    requestBody: { values },
  })
}
