// Flat config (Next.js 16 removed `next lint`; ESLint is run directly: `npm run lint`).
// Next's recommended rules, plus React hooks and Core Web Vitals rules, with TypeScript support.
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import { defineConfig, globalIgnores } from "eslint/config";

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    // Valid patterns here (a "mounted" flag, reading localStorage after load); rewriting them risks
    // behavior the tests rely on. Tracked as P-16 in the improvement backlog.
    rules: { "react-hooks/set-state-in-effect": "warn" },
  },
  globalIgnores([".next/**", "out/**", "coverage/**", "next-env.d.ts", "src/lib/api/schema.d.ts", "e2e/.results/**", "playwright-report/**", "public/**"]),
]);
