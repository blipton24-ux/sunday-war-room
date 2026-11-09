/**
 * Builds the FastAPI URL for a browser request to /api/v1/<path> (ADR-036). Pure, so it is
 * unit tested: the pass-through must never reach anything outside /api/v1 on the API.
 */
export class BadProxyPath extends Error {}

export function upstreamUrl(segments: readonly string[], search: string, apiBase: string): URL {
  if (segments.length === 0) throw new BadProxyPath("empty path");
  for (const raw of segments) {
    // Next has already percent-decoded each segment; reject anything that could climb out
    // of /api/v1 once re-joined ("..", ".", encoded slashes, backslashes, empty).
    if (raw === "" || raw === "." || raw === ".." || /[/\\]/.test(raw)) {
      throw new BadProxyPath(`bad path segment: ${JSON.stringify(raw)}`);
    }
  }
  const path = segments.map(encodeURIComponent).join("/");
  const url = new URL(`/api/v1/${path}`, apiBase);
  if (!url.pathname.startsWith("/api/v1/")) throw new BadProxyPath("path escaped /api/v1");
  url.search = search;
  return url;
}
