// Generates src/lib/api/schema.d.ts from ../api/openapi.json (ADR-014).
//
//   npm run generate:api   writes the file
//   npm run check:api      exits 1 if the committed file is stale (used by CI)
//
// One code path for both, so CI and a local run can never disagree.
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const here = dirname(fileURLToPath(import.meta.url));
const specPath = resolve(here, "../../api/openapi.json");
const outPath = resolve(here, "../src/lib/api/schema.d.ts");

const HEADER = `/**
 * GENERATED FILE. Do not edit by hand.
 * Source: api/openapi.json (FastAPI). Regenerate with \`npm run generate:api\`.
 */

`;

const spec = JSON.parse(readFileSync(specPath, "utf8"));
const generated = HEADER + astToString(await openapiTS(spec)).replace(/\r\n/g, "\n");

if (process.argv.includes("--check")) {
  const committed = existsSync(outPath) ? readFileSync(outPath, "utf8").replace(/\r\n/g, "\n") : "";
  if (committed !== generated) {
    console.error(
      "src/lib/api/schema.d.ts is out of date with api/openapi.json.\n" +
        "Run `npm run generate:api` and commit the result.",
    );
    process.exit(1);
  }
  console.log("API client types are up to date");
} else {
  writeFileSync(outPath, generated, "utf8");
  console.log(`wrote ${outPath}`);
}
