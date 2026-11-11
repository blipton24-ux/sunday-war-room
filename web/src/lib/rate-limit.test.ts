import { describe, expect, it } from "vitest";

import { createRateLimiter } from "./rate-limit";

describe("createRateLimiter", () => {
  it("allows up to the limit, then refuses", () => {
    const limiter = createRateLimiter(2, 60_000, () => 0);
    expect([limiter.take("a"), limiter.take("a"), limiter.take("a")]).toEqual([true, true, false]);
  });

  it("counts each key on its own", () => {
    const limiter = createRateLimiter(1, 60_000, () => 0);
    expect(limiter.take("ana")).toBe(true);
    expect(limiter.take("bob")).toBe(true);
    expect(limiter.take("ana")).toBe(false);
  });

  it("lets a key through again once its window has passed", () => {
    let t = 0;
    const limiter = createRateLimiter(1, 60_000, () => t);
    expect(limiter.take("a")).toBe(true);
    t = 59_999;
    expect(limiter.take("a")).toBe(false);
    t = 60_000;
    expect(limiter.take("a")).toBe(true);
  });

  it("does not extend the wait for hits that were refused", () => {
    let t = 0;
    const limiter = createRateLimiter(1, 60_000, () => t);
    limiter.take("a");
    t = 30_000;
    expect(limiter.take("a")).toBe(false); // refused, so it must not push the window out
    t = 60_000;
    expect(limiter.take("a")).toBe(true);
  });
});
