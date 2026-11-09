/**
 * Safety rules about secrets and sign-in emails, kept free of imports so they can be unit
 * tested. env.ts and email.ts apply them.
 */

/** True for an address that only exists on this machine. */
export function isLocalUrl(url: string): boolean {
  try {
    return ["localhost", "127.0.0.1", "[::1]"].includes(new URL(url).hostname);
  } catch {
    return false;
  }
}

/**
 * Without a Resend key, the sign-in link may be written to the server log, but ONLY when the
 * app's address is on this machine. A public deployment can never expose links in its logs,
 * even if someone forgets to set the key: it refuses to send instead.
 */
export function canLogMagicLinks(appUrl: string, hasResendKey: boolean): boolean {
  return !hasResendKey && isLocalUrl(appUrl);
}

/** Secrets that ship in .env.example and docker-compose.yml. Fine locally, never in production. */
export const DEV_SECRETS: ReadonlySet<string> = new Set([
  "dev-only-better-auth-secret-change-me-0123456789",
  "dev-only-secret-change-me-0123456789abcdef",
]);

/** Throws when a public production deployment is using a known development secret. */
export function assertNotDevSecret(name: string, value: string, appUrl: string, production: boolean): void {
  if (production && !isLocalUrl(appUrl) && DEV_SECRETS.has(value)) {
    throw new Error(`${name} is still the development value: set a real secret for this deployment`);
  }
}
