// Starts and stops the end-to-end test stack (docker-compose.yml + docker-compose.e2e.yml).
//
//   node e2e/stack.mjs up      fresh database, build, seed, wait until everything is healthy
//   node e2e/stack.mjs down    stop and delete its data
//   node e2e/stack.mjs logs [service]
//
// It uses its own Docker project name and ports, so it never touches your development stack
// (database on 5432, API on 8000, web on 3000). Works the same on Windows, macOS and Linux.
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");

export const PORTS = { db: 55432, redis: 56379, api: 18000, web: 13000 };
const env = {
  ...process.env,
  DB_PORT: String(PORTS.db),
  REDIS_PORT: String(PORTS.redis),
  API_PORT: String(PORTS.api),
  WEB_PORT: String(PORTS.web),
  BETTER_AUTH_URL: `http://localhost:${PORTS.web}`,
};
const compose = [
  "compose", "-p", "swr-e2e",
  "-f", "docker-compose.yml", "-f", "docker-compose.e2e.yml",
]; // prettier-ignore

function run(args, { allowFail = false } = {}) {
  const result = spawnSync("docker", [...compose, ...args], { cwd: root, env, stdio: "inherit" });
  if (result.status !== 0 && !allowFail) process.exit(result.status ?? 1);
  return result.status === 0;
}

const [command, ...rest] = process.argv.slice(2);
if (command === "up") {
  run(["down", "-v", "--remove-orphans"], { allowFail: true }); // always start from nothing
  run(["up", "-d", "--build", "--wait", "--wait-timeout", "300"]);
  console.log(`\ne2e stack is up: web http://localhost:${PORTS.web}, db localhost:${PORTS.db}`);
} else if (command === "down") {
  run(["down", "-v", "--remove-orphans"]);
} else if (command === "logs") {
  run(["logs", "--no-color", ...rest]);
} else {
  console.error("usage: node e2e/stack.mjs up | down | logs [service]");
  process.exit(2);
}
