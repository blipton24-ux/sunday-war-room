// Liveness check for Docker and the hosting platform. Public and dependency-free on purpose:
// it answers "is the web server running", not "is everything behind it healthy".
export const dynamic = "force-dynamic";

export function GET() {
  return Response.json({ status: "ok" }, { headers: { "cache-control": "no-store" } });
}
