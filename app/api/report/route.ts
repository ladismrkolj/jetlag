import { NextRequest, NextResponse } from 'next/server'
import nodemailer from 'nodemailer'
import { google } from 'googleapis'

export async function POST(req: NextRequest) {
  let payload: any
  try {
    payload = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }

  const host = process.env.MAIL_HOST
  const port = Number(process.env.MAIL_PORT || '587')
  const user = process.env.MAIL_USER
  const pass = process.env.MAIL_PASS
  const from = process.env.MAIL_FROM || 'info@surfsplit.com'
  const to = process.env.MAIL_TO || 'info@surfsplit.com'
  const secure = process.env.MAIL_SECURE === 'true' || port === 465

  const summary = {
    comment: payload?.comment ?? '',
    inputs: payload?.inputs ?? null,
    dataSample: Array.isArray(payload?.data) ? payload.data.slice(0, 10) : payload?.data ?? null,
    counts: Array.isArray(payload?.data) ? { events: payload.data.length } : undefined,
    userAgent: payload?.userAgent ?? 'unknown',
    url: payload?.url ?? 'unknown',
    ts: new Date().toISOString(),
  }

  // If SMTP not configured, log and accept so users aren't blocked
  if (!host || !user || !pass) {
    console.error('[report] SMTP not configured. Summary:', summary)
    return NextResponse.json({ ok: true, noted: true })
  }

  const transporter = nodemailer.createTransport({ host, port, secure, auth: { user, pass } })

  const subject = `Jet Lag Planner feedback — ${summary.ts}`
  const text = [
    `Feedback received at ${summary.ts}`,
    '',
    summary.comment ? `User comment:\n${summary.comment}\n` : 'No user comment provided.\n',
    'Context summary attached (debug.json).',
  ].join('\n')

  // Prepare attachments (debug JSON + optional screenshot)
  const attachments: any[] = []
  // Attach sanitized debug JSON (exclude screenshot data URL)
  ;(() => {
    try {
      const { screenshot: _omit, ...rest } = (payload || {})
      attachments.push({ filename: 'debug.json', content: Buffer.from(JSON.stringify(rest, null, 2)), contentType: 'application/json' })
    } catch {}
  })()
  const dataUrl: string | undefined = payload?.screenshot
  if (dataUrl && typeof dataUrl === 'string' && dataUrl.startsWith('data:image/')) {
    const m = /^data:(.+);base64,(.*)$/.exec(dataUrl)
    if (m) {
      const mime = m[1]
      const b64 = m[2]
      attachments.push({ filename: `screenshot.${mime.includes('jpeg') ? 'jpg' : 'png'}`, content: Buffer.from(b64, 'base64'), contentType: mime })
    }
  }

  try {
    await transporter.sendMail({ from, to, subject, text, attachments })
    // Fire-and-forget append to Google Sheets (best-effort)
    try {
      await appendToSheet(req, payload)
    } catch (e) {
      console.error('[report] sheets append error', e)
    }
    return NextResponse.json({ ok: true })
  } catch (e: any) {
    console.error('[report] send error', e)
    return NextResponse.json({ error: e?.message || 'Send failed' }, { status: 500 })
  }
}

async function appendToSheet(req: NextRequest, payload: any) {
  const sheetId = process.env.GOOGLE_SHEETS_ID
  const sheetTab = process.env.GOOGLE_SHEETS_TAB || 'Sheet1'
  const clientEmail = process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL
  const privateKeyRaw = process.env.GOOGLE_PRIVATE_KEY
  if (!sheetId || !clientEmail || !privateKeyRaw) return

  const privateKey = privateKeyRaw.replace(/\\n/g, '\n')
  const auth = new google.auth.JWT({
    email: clientEmail,
    key: privateKey,
    scopes: ['https://www.googleapis.com/auth/spreadsheets']
  })
  const sheets = google.sheets({ version: 'v4', auth })

  // Build a sanitized row (do not include big blobs like screenshot or slots/data)
  const now = new Date().toISOString()
  const ip = req.headers.get('x-forwarded-for') || ''
  const ua = payload?.userAgent || req.headers.get('user-agent') || ''
  const url = payload?.url || ''
  const type = payload?.type || (payload?.rating ? 'quick_feedback' : 'report')
  const rating = payload?.rating || ''
  const source = payload?.source || ''
  const email = (payload?.email || '').toString()
  const nameSuggestion = payload?.nameSuggestion || ''
  const comment = payload?.comment || payload?.message || payload?.inputs?.message || ''
  const originOffset = payload?.inputs?.originOffset ?? ''
  const destOffset = payload?.inputs?.destOffset ?? ''
  const preDays = payload?.inputs?.preDays ?? ''

  const values = [[
    now,
    type,
    rating,
    source,
    email,
    nameSuggestion,
    comment,
    originOffset,
    destOffset,
    preDays,
    ua,
    ip,
    url,
  ]]

  await sheets.spreadsheets.values.append({
    spreadsheetId: sheetId,
    range: `${sheetTab}!A1`,
    valueInputOption: 'RAW',
    requestBody: { values },
  })
}
