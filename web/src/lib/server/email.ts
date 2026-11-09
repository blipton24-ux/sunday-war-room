import "server-only";

import { env } from "./env";

/**
 * Sends the magic sign-in link (ADR-029: Resend).
 *
 * Without RESEND_API_KEY in local development, the link is printed to the server log so
 * sign-in works with no email account. In production a missing key is an error.
 */
export async function sendMagicLinkEmail(to: string, url: string): Promise<void> {
  if (!env.resendApiKey) {
    if (env.isProduction) throw new Error("RESEND_API_KEY is not set: cannot send sign-in email");
    console.info(`\n[dev] Magic sign-in link for ${to}:\n${url}\n`);
    return;
  }
  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${env.resendApiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      from: env.emailFrom,
      to,
      subject: "Your Sunday War Room sign-in link",
      text: `Sign in to Sunday War Room:\n\n${url}\n\nThis link works once and expires in 10 minutes. If you didn't ask for it, ignore this email.`,
      html: magicLinkHtml(url),
    }),
  });
  if (!response.ok) {
    throw new Error(`Resend rejected the sign-in email: HTTP ${response.status}`);
  }
}

function magicLinkHtml(url: string): string {
  const safe = url.replace(/"/g, "&quot;");
  return `<div style="font-family:Inter,Arial,sans-serif;background:#0b1016;color:#efe8da;padding:32px">
  <div style="max-width:420px;margin:0 auto;background:#141e28;border-radius:20px;padding:28px">
    <h1 style="font-size:20px;margin:0 0 12px">Sunday <span style="color:#e6b95c">War Room</span></h1>
    <p style="color:#c3cad1;margin:0 0 20px">Tap the button to sign in. It works once and expires in 10 minutes.</p>
    <a href="${safe}" style="display:inline-block;background:#e6b95c;color:#1b1406;font-weight:800;text-decoration:none;padding:12px 20px;border-radius:14px">Sign in</a>
    <p style="color:#8d99a6;font-size:12px;margin:20px 0 0">If you didn't ask for this, you can ignore it.</p>
  </div></div>`;
}
