// Prints the SQL Better Auth would run to create its tables, for our field mapping.
//
//   AUTH_SCHEMA_DATABASE_URL=postgres://.../empty_db npm run auth:schema
//
// Point it at an EMPTY database so the output is the full schema. It never changes any
// database: Alembic (api/alembic) owns the schema, and this output is the spec its
// migration must match (ADR-035). Runs with Node's built-in TypeScript support.
import { getMigrations } from "better-auth/db/migration";
import { magicLink } from "better-auth/plugins/magic-link";
import { Pool } from "pg";

import { authSchemaOptions } from "../src/lib/server/auth-schema.ts";

const url = process.env.AUTH_SCHEMA_DATABASE_URL;
if (!url) {
  console.error("Set AUTH_SCHEMA_DATABASE_URL to an empty Postgres database");
  process.exit(2);
}
const pool = new Pool({ connectionString: url });
const { compileMigrations, toBeCreated, toBeAdded } = await getMigrations({
  ...authSchemaOptions,
  database: pool,
  plugins: [magicLink({ sendMagicLink: async () => {} })],
});
console.log(`-- tables to create: ${toBeCreated.map((t) => t.table).join(", ") || "none"}`);
console.log(`-- columns to add: ${toBeAdded.map((t) => t.table).join(", ") || "none"}`);
console.log(await compileMigrations());
await pool.end();
