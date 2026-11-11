/**
 * A tiny in-memory rate limiter: at most `max` hits per key inside a sliding window.
 *
 * In memory means per server process, which is the right scale for "don't let one user send
 * themselves a hundred emails" on a single web server. It is not a cross-server limit; if the
 * web tier is ever scaled out, move this to Redis (backlog).
 */
export function createRateLimiter(max: number, windowMs: number, now: () => number = Date.now) {
  const hits = new Map<string, number[]>();
  return {
    /** Records a hit and returns true if it is allowed; false (and nothing recorded) if over. */
    take(key: string): boolean {
      const current = now();
      const recent = (hits.get(key) ?? []).filter((t) => current - t < windowMs);
      if (recent.length >= max) {
        hits.set(key, recent);
        return false;
      }
      recent.push(current);
      hits.set(key, recent);
      return true;
    },
  };
}
