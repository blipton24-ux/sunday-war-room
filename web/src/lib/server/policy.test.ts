import { describe, expect, it } from "vitest";

import { DEV_SECRETS, assertNotDevSecret, canLogMagicLinks, isLocalUrl } from "./policy";

describe("isLocalUrl", () => {
  it.each(["http://localhost:3000", "http://127.0.0.1:13000/x", "http://[::1]:3000"])("%s is local", (u) => {
    expect(isLocalUrl(u)).toBe(true);
  });
  it.each([
    "https://sundaywarroom.app",
    "http://localhost.evil.com",
    "http://192.168.1.20:3000", // another device on the network can see this one
    "not a url",
    "",
  ])("%s is not", (u) => {
    expect(isLocalUrl(u)).toBe(false);
  });
});

describe("canLogMagicLinks", () => {
  it("only without a Resend key and only on this machine", () => {
    expect(canLogMagicLinks("http://localhost:3000", false)).toBe(true);
    expect(canLogMagicLinks("http://localhost:3000", true)).toBe(false); // a real key means really send
    expect(canLogMagicLinks("https://sundaywarroom.app", false)).toBe(false); // never on a public site
  });
});

describe("assertNotDevSecret", () => {
  const dev = [...DEV_SECRETS][0]!;
  it("refuses a development secret on a public production site", () => {
    expect(() => assertNotDevSecret("API_JWT_SECRET", dev, "https://sundaywarroom.app", true)).toThrow(
      /development value/,
    );
  });
  it("allows it locally, in development, or when it is a real secret", () => {
    expect(() => assertNotDevSecret("X", dev, "http://localhost:3000", true)).not.toThrow();
    expect(() => assertNotDevSecret("X", dev, "https://sundaywarroom.app", false)).not.toThrow();
    expect(() => assertNotDevSecret("X", "a-real-random-secret", "https://sundaywarroom.app", true)).not.toThrow();
  });
});

describe("/api/health", () => {
  it("answers ok without touching anything else", async () => {
    const { GET } = await import("@/app/api/health/route");
    const res = GET();
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ status: "ok" });
    expect(res.headers.get("cache-control")).toBe("no-store");
  });
});
