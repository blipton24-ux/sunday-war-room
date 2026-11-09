/**
 * Runs the real public/sw.js in a sandbox with a fake cache and fake events (ADR-038).
 * The rules under test: never touch /api/*, never store a page, serve the offline page when
 * the network fails, keep content-hashed static files.
 */
import { readFileSync } from "node:fs";
import vm from "node:vm";

import { beforeEach, describe, expect, it, vi } from "vitest";

const SOURCE = readFileSync(new URL("../public/sw.js", import.meta.url), "utf8");
const ORIGIN = "https://app.test";

/** Just enough of the Cache Storage API. Requests are keyed by URL. */
class FakeCache {
  entries = new Map<string, Response>();
  puts: string[] = [];
  async addAll(urls: string[]) {
    for (const u of urls) this.entries.set(new URL(u, ORIGIN).href, new Response(`precached ${u}`));
  }
  async match(req: string | Request) {
    return this.entries.get(typeof req === "string" ? new URL(req, ORIGIN).href : req.url)?.clone();
  }
  async put(req: Request, res: Response) {
    this.puts.push(req.url);
    this.entries.set(req.url, res);
  }
  async keys() {
    return [...this.entries.keys()].map((u) => new Request(u));
  }
  async delete(req: Request | string) {
    return this.entries.delete(typeof req === "string" ? req : req.url);
  }
}

class FakeCacheStorage {
  caches = new Map<string, FakeCache>();
  async open(name: string) {
    if (!this.caches.has(name)) this.caches.set(name, new FakeCache());
    return this.caches.get(name)!;
  }
  async keys() {
    return [...this.caches.keys()];
  }
  async delete(name: string) {
    return this.caches.delete(name);
  }
}

interface FetchResult {
  intercepted: boolean;
  response?: Response;
}

function boot(network: (req: Request) => Promise<Response>) {
  const listeners: Record<string, (e: unknown) => void> = {};
  const storage = new FakeCacheStorage();
  const fetchSpy = vi.fn(network);
  const self = {
    location: { origin: ORIGIN },
    addEventListener: (type: string, fn: (e: unknown) => void) => (listeners[type] = fn),
    skipWaiting: vi.fn(async () => {}),
    clients: { claim: vi.fn(async () => {}) },
  };
  const context = vm.createContext({
    self, caches: storage, fetch: fetchSpy, URL, Request, Response, Promise, Math, Set,
  }); // prettier-ignore
  vm.runInContext(SOURCE, context);

  async function lifecycle(type: "install" | "activate") {
    const pending: Promise<unknown>[] = [];
    listeners[type]!({ waitUntil: (p: Promise<unknown>) => pending.push(p) });
    await Promise.all(pending);
  }

  async function request(
    url: string,
    init: { method?: string; mode?: RequestMode } = {},
  ): Promise<FetchResult> {
    // sw.js reads only method, url and mode from a request. A plain object stands in for it
    // because script can't create a real Request with mode "navigate".
    const fake = {
      method: init.method ?? "GET",
      url: new URL(url, ORIGIN).href,
      mode: init.mode ?? "no-cors",
    } as unknown as Request;
    let responded: Promise<Response> | undefined;
    const pending: Promise<unknown>[] = [];
    listeners.fetch!({
      request: fake,
      respondWith: (p: Promise<Response>) => (responded = p),
      waitUntil: (p: Promise<unknown>) => pending.push(p),
    });
    const response = responded ? await responded : undefined;
    await Promise.all(pending);
    return { intercepted: responded !== undefined, response };
  }

  return { storage, fetchSpy, self, lifecycle, request };
}

const ok = (body = "ok") => async () => new Response(body, { status: 200 });
const down = async () => {
  throw new TypeError("Failed to fetch");
};

describe("install and activate", () => {
  it("precaches the offline page and icons, then takes over at once", async () => {
    const sw = boot(ok());
    await sw.lifecycle("install");
    const shell = await sw.storage.open("swr-shell-v1");
    expect([...shell.entries.keys()].map((u) => new URL(u).pathname).sort()).toEqual([
      "/icons/icon-192.png",
      "/icons/icon-512.png",
      "/offline.html",
    ]);
    expect(sw.self.skipWaiting).toHaveBeenCalled();
  });

  it("deletes only its own old caches", async () => {
    const sw = boot(ok());
    await sw.storage.open("swr-static-v0");
    await sw.storage.open("swr-shell-v1");
    await sw.storage.open("someone-elses-cache");
    await sw.lifecycle("activate");
    expect(await sw.storage.keys()).toEqual(["swr-shell-v1", "someone-elses-cache"]);
    expect(sw.self.clients.claim).toHaveBeenCalled();
  });
});

describe("privacy: what it never touches", () => {
  let sw: ReturnType<typeof boot>;
  beforeEach(async () => {
    sw = boot(ok("secret league data"));
    await sw.lifecycle("install");
  });

  // Every way a request can reach the worker: fetch() from a page ("cors"), subresources
  // ("no-cors"), and a top-level page load ("navigate", which is how a magic link arrives).
  it.each(
    ["/api/v1/me", "/api/v1/leagues/7/matchup?week=9", "/api/auth/get-session", "/api/auth/magic-link/verify?token=abc"]
      .flatMap((path) => (["cors", "no-cors", "navigate"] as const).map((mode) => [path, mode] as const)),
  )("leaves %s (%s) entirely to the network", async (path, mode) => {
    const r = await sw.request(path, { mode });
    expect(r.intercepted).toBe(false);
    expect(sw.fetchSpy).not.toHaveBeenCalled();
  });

  it("ignores writes and other sites", async () => {
    expect((await sw.request("/api/v1/leagues", { method: "POST" })).intercepted).toBe(false);
    expect((await sw.request("/lineup", { method: "POST", mode: "navigate" })).intercepted).toBe(false);
    expect((await sw.request("https://a.espncdn.com/i/headshots/x.png")).intercepted).toBe(false);
  });

  it("never stores a page, or anything outside /_next/static", async () => {
    await sw.request("/lineup", { mode: "navigate" });
    await sw.request("/settings", { mode: "navigate" });
    await sw.request("/_next/image?url=x&w=96");
    await sw.request("/manifest.webmanifest");
    const stored = [...sw.storage.caches.values()].flatMap((c) => c.puts);
    expect(stored).toEqual([]);
  });
});

describe("page loads", () => {
  it("shows the real page when the network works", async () => {
    const sw = boot(ok("<html>lineup</html>"));
    await sw.lifecycle("install");
    const r = await sw.request("/lineup", { mode: "navigate" });
    expect(r.intercepted).toBe(true);
    expect(await r.response!.text()).toBe("<html>lineup</html>");
  });

  it("shows the offline page when it fails", async () => {
    const sw = boot(down);
    await sw.lifecycle("install");
    const r = await sw.request("/lineup", { mode: "navigate" });
    expect(await r.response!.text()).toBe("precached /offline.html");
  });

  it("passes server errors through instead of pretending to be offline", async () => {
    const sw = boot(async () => new Response("bad gateway", { status: 502 }));
    await sw.lifecycle("install");
    const r = await sw.request("/lineup", { mode: "navigate" });
    expect(r.response!.status).toBe(502);
  });
});

describe("static files", () => {
  it("keeps content-hashed files and serves them without the network next time", async () => {
    const sw = boot(ok("console.log(1)"));
    await sw.lifecycle("install");
    const first = await sw.request("/_next/static/chunks/app-abc123.js");
    expect(await first.response!.text()).toBe("console.log(1)");
    expect(sw.fetchSpy).toHaveBeenCalledTimes(1);

    const second = await sw.request("/_next/static/chunks/app-abc123.js");
    expect(await second.response!.text()).toBe("console.log(1)");
    expect(sw.fetchSpy).toHaveBeenCalledTimes(1); // from the cache
  });

  it("does not keep failed responses", async () => {
    const sw = boot(async () => new Response("missing", { status: 404 }));
    await sw.lifecycle("install");
    await sw.request("/_next/static/chunks/gone.js");
    const cache = await sw.storage.open("swr-static-v1");
    expect(cache.entries.size).toBe(0);
  });

  it("stays bounded, dropping the oldest files first", async () => {
    const sw = boot(ok("x"));
    await sw.lifecycle("install");
    for (let i = 0; i < 125; i++) await sw.request(`/_next/static/chunks/f${i}.js`);
    const cache = await sw.storage.open("swr-static-v1");
    expect(cache.entries.size).toBe(120);
    expect(cache.entries.has(`${ORIGIN}/_next/static/chunks/f0.js`)).toBe(false);
    expect(cache.entries.has(`${ORIGIN}/_next/static/chunks/f124.js`)).toBe(true);
  });
});
