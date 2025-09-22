import { NextRequest, NextResponse } from 'next/server'
import { spawn } from 'child_process'
import fs from 'fs'
import path from 'path'

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
  shiftOnTravelDays: boolean
  preDays: number
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
