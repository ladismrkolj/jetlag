import { NextRequest, NextResponse } from 'next/server'
import nodemailer from 'nodemailer'

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
    return NextResponse.json({ ok: true })
  } catch (e: any) {
    console.error('[report] send error', e)
    return NextResponse.json({ error: e?.message || 'Send failed' }, { status: 500 })
  }
}
