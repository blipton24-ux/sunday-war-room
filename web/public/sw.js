/*
 * Sunday War Room service worker (ADR-038).
 *
 * What it does
 *   - Precaches /offline.html and the app icons when it installs.
 *   - Page loads: network first. If the network fails, it shows /offline.html. HTML is never stored.
 *   - /_next/static/*: cache first. These files have a content hash in their name and never
 *     change, so a cached copy can never be stale.
 *
 * What it never does
 *   - It never touches /api/* (sign-in, your leagues, projections) or any cross-origin request,
 *     and it never stores a page. Nothing about a user is cached, so there is nothing to leak on a
 *     shared phone and nothing to clear on sign-out. Showing last-known numbers offline is a
 *     separate feature (docs/Build-Plan/Improvement-Backlog.md, U-11).
 *
 * Plain JavaScript, no build step: tests/sw.test.ts runs this exact file.
 */
const VERSION = "v1";
const SHELL_CACHE = `swr-shell-${VERSION}`;
const STATIC_CACHE = `swr-static-${VERSION}`;
const PRECACHE = ["/offline.html", "/icons/icon-192.png", "/icons/icon-512.png"];
const MAX_STATIC_ENTRIES = 120;

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keep = new Set([SHELL_CACHE, STATIC_CACHE]);
      for (const name of await caches.keys()) {
        // Only our own old caches; never anything else on this origin.
        if (name.startsWith("swr-") && !keep.has(name)) await caches.delete(name);
      }
      await self.clients.claim();
    })(),
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/")) return; // never intercepted: always straight to the network

  if (request.mode === "navigate") {
    event.respondWith(showPageOrOffline(request));
  } else if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith(cacheFirst(event, request));
  }
});

async function showPageOrOffline(request) {
  try {
    return await fetch(request);
  } catch {
    const cache = await caches.open(SHELL_CACHE);
    return (await cache.match("/offline.html")) || Response.error();
  }
}

async function cacheFirst(event, request) {
  const cache = await caches.open(STATIC_CACHE);
  const hit = await cache.match(request);
  if (hit) return hit;
  const response = await fetch(request);
  if (response.ok) {
    await cache.put(request, response.clone());
    event.waitUntil(trim(cache));
  }
  return response;
}

/** Keep the static cache bounded: drop the oldest entries first. */
async function trim(cache) {
  const keys = await cache.keys();
  for (const key of keys.slice(0, Math.max(0, keys.length - MAX_STATIC_ENTRIES))) {
    await cache.delete(key);
  }
}
