import "server-only";

import { betterAuth } from "better-auth";
import { nextCookies } from "better-auth/next-js";
import { magicLink } from "better-auth/plugins/magic-link";
import { Pool } from "pg";

import { authSchemaOptions } from "./auth-schema";
import { sendMagicLinkEmail } from "./email";
import { env, googleEnabled } from "./env";

/**
 * Sign-in (ADR-035): Google + email magic links, users in our PostgreSQL.
 *
 * The tables are created and changed only by Alembic (api/alembic); `authSchemaOptions` maps
 * Better Auth's fields onto them. Integer ids ("serial") keep users.id the integer the API's
 * token carries.
 */
function createAuth() {
  return betterAuth({
  appName: "Sunday War Room",
  baseURL: env.appUrl,
  secret: env.authSecret,
  database: new Pool({ connectionString: env.authDatabaseUrl, max: 5 }),
  ...authSchemaOptions,
  session: {
    ...authSchemaOptions.session,
    expiresIn: 60 * 60 * 24 * 30, // 30 days
    updateAge: 60 * 60 * 24, // refresh the expiry at most once a day
  },
  socialProviders: googleEnabled()
    ? { google: { clientId: env.googleClientId!, clientSecret: env.googleClientSecret! } }
    : {},
  plugins: [
    magicLink({
      expiresIn: 60 * 10,
      sendMagicLink: async ({ email, url }) => sendMagicLinkEmail(email, url),
    }),
    nextCookies(), // must stay last: lets server actions set the session cookie
  ],
  });
}

let instance: ReturnType<typeof createAuth> | undefined;

/** The Better Auth instance, created on first use (not at import, so builds need no secrets). */
export function getAuth() {
  return (instance ??= createAuth());
}

export type Session = ReturnType<typeof createAuth>["$Infer"]["Session"];
