import { Resend } from "resend"

let resend: Resend | null = null

function getResend(): Resend | null {
  if (!process.env.RESEND_API_KEY) return null
  if (!resend) resend = new Resend(process.env.RESEND_API_KEY)
  return resend
}

export async function sendEmail(opts: {
  to: string
  subject: string
  text: string
  from?: string
}): Promise<boolean> {
  const r = getResend()
  if (!r) return false
  try {
    await r.emails.send({
      from: opts.from ?? "UnpauseAI <no-reply@unpauseai.com>",
      to: opts.to,
      subject: opts.subject,
      text: opts.text,
    })
    return true
  } catch (err) {
    console.error("Failed to send email:", opts.subject, err)
    return false
  }
}

export async function notifyAdmin(subject: string, text: string) {
  const adminEmail =
    process.env.ADMIN_NOTIFICATION_EMAIL ?? "admin@unpauseai.com"
  return sendEmail({ to: adminEmail, subject, text })
}
