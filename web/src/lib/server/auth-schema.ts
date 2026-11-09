/**
 * How Better Auth's records map onto OUR tables (ADR-035). Kept free of imports so the
 * schema script (scripts/auth-schema.ts) and the app read the exact same object.
 *
 * Alembic owns these tables (api/alembic). After changing anything here, run
 * `npm run auth:schema` against an empty database and update the migration to match.
 */
export const authSchemaOptions = {
  advanced: { database: { generateId: "serial" as const } },
  user: {
    modelName: "users",
    fields: { emailVerified: "email_verified", createdAt: "created_at", updatedAt: "updated_at" },
  },
  session: {
    modelName: "sessions",
    fields: {
      userId: "user_id",
      expiresAt: "expires_at",
      ipAddress: "ip_address",
      userAgent: "user_agent",
      createdAt: "created_at",
      updatedAt: "updated_at",
    },
  },
  account: {
    modelName: "accounts",
    fields: {
      userId: "user_id",
      accountId: "account_id",
      providerId: "provider_id",
      accessToken: "access_token",
      refreshToken: "refresh_token",
      idToken: "id_token",
      accessTokenExpiresAt: "access_token_expires_at",
      refreshTokenExpiresAt: "refresh_token_expires_at",
      createdAt: "created_at",
      updatedAt: "updated_at",
    },
  },
  verification: {
    modelName: "verifications",
    fields: { expiresAt: "expires_at", createdAt: "created_at", updatedAt: "updated_at" },
  },
};
