import { existsSync, readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { installState, isIos } from "@/lib/install";

import manifest from "./manifest";

const web = new URL("../../", import.meta.url);

/** Pixel size from a PNG's header (IHDR: width and height at bytes 16-23). */
function pngSize(path: URL): string {
  const b = readFileSync(path);
  return `${b.readUInt32BE(16)}x${b.readUInt32BE(20)}`;
}

describe("web app manifest", () => {
  const m = manifest();

  it("has what Chrome and Safari need to treat the site as installable", () => {
    expect(m.name).toBe("Sunday War Room");
    expect(m.short_name).toBeTruthy();
    expect(m.short_name!.length).toBeLessThanOrEqual(12); // fits under a home-screen icon
    expect(m.display).toBe("standalone");
    expect(m.start_url).toBe("/");
    expect(m.scope).toBe("/");
    expect(m.background_color).toBe("#0b1016");
    expect(m.theme_color).toBe("#0b1016");
  });

  it("lists real icon files at the sizes it claims", () => {
    for (const icon of m.icons!.filter((i) => i.type === "image/png")) {
      const file = new URL(`public${icon.src}`, web);
      expect(existsSync(file), icon.src).toBe(true);
      expect(pngSize(file), icon.src).toBe(icon.sizes);
    }
  });

  it("has a 192, a 512 and a separate maskable icon", () => {
    const sizes = m.icons!.filter((i) => i.purpose === "any").map((i) => i.sizes);
    expect(sizes).toEqual(expect.arrayContaining(["192x192", "512x512"]));
    const maskable = m.icons!.filter((i) => i.purpose === "maskable");
    expect(maskable).toHaveLength(1); // its own file: a maskable icon looks wrong uncropped
  });

  it("has an Apple touch icon and an SVG favicon where Next.js looks for them", () => {
    expect(pngSize(new URL("src/app/apple-icon.png", web))).toBe("180x180");
    expect(existsSync(new URL("src/app/icon.svg", web))).toBe(true);
  });

  it("only offers shortcuts to screens that exist", () => {
    for (const s of m.shortcuts ?? []) {
      expect(existsSync(new URL(`src/app/(app)${s.url}/page.tsx`, web)), s.url).toBe(true);
    }
  });

  it("has the offline page the service worker precaches", () => {
    const page = readFileSync(new URL("public/offline.html", web), "utf8");
    expect(page).toContain("You're offline");
    expect(page).not.toMatch(/<(script|link)[^>]+(src|href)=/); // nothing external to fail to load
  });
});

describe("install card state", () => {
  it("picks the right message for each device", () => {
    expect(installState({ standalone: true, hasPrompt: false, ios: false })).toBe("installed");
    expect(installState({ standalone: true, hasPrompt: true, ios: true })).toBe("installed");
    expect(installState({ standalone: false, hasPrompt: true, ios: false })).toBe("can-prompt");
    expect(installState({ standalone: false, hasPrompt: false, ios: true })).toBe("ios");
    expect(installState({ standalone: false, hasPrompt: false, ios: false })).toBe("manual");
  });

  it("recognizes iPhones, iPads and iPadOS", () => {
    expect(isIos("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)", "iPhone", 5)).toBe(true);
    expect(isIos("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", "MacIntel", 5)).toBe(true); // iPadOS
    expect(isIos("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", "MacIntel", 0)).toBe(false); // a Mac
    expect(isIos("Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Win32", 0)).toBe(false);
  });
});
