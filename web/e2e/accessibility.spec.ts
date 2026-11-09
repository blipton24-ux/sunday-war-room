/**
 * Automated accessibility checks (axe, WCAG 2.0/2.1 A and AA rules) on every screen in both
 * themes, plus a look at each (screenshots attached). Verification Gaps V-10.
 *
 * Automated checks catch about a third of accessibility problems: contrast, missing names and
 * labels, bad structure. They don't replace trying the app with a screen reader.
 */
import AxeBuilder from "@axe-core/playwright";
import { mkdirSync, writeFileSync } from "node:fs";

import { expect, test } from "@playwright/test";

// Reports and screenshots land here (git-ignored) so they can be reviewed after a run.
const OUT = "e2e/.results/a11y";

const SCREENS: [path: string, ready: RegExp][] = [
  ["/", /^Week 9$/],
  ["/lineup", /^Lineup$/],
  ["/matchup", /^Matchup$/],
  ["/accuracy", /^Accuracy$/],
  ["/settings", /^Settings$/],
];

for (const theme of ["dark", "light"] as const) {
  test.describe(`${theme} theme`, () => {
    test.use({ colorScheme: theme });
    test.beforeEach(async ({ page }) => {
      await page.addInitScript((t) => localStorage.setItem("theme", t), theme);
    });

    for (const [path, ready] of SCREENS) {
      test(`${path} has no serious accessibility problems`, async ({ page }, testInfo) => {
        await page.goto(path);
        await expect(page.getByRole("heading", { name: ready })).toBeVisible();
        await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
        await page.waitForLoadState("networkidle");
        if (path === "/lineup") await page.getByRole("button", { name: /Zay Flowers/ }).click(); // open state too

        const results = await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
          .analyze();
        const name = `${theme}-${path === "/" ? "home" : path.slice(1)}`;
        mkdirSync(OUT, { recursive: true });
        writeFileSync(`${OUT}/${name}.axe.json`, JSON.stringify(results.violations, null, 2));
        await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true });
        await testInfo.attach(`${name}.png`, { path: `${OUT}/${name}.png` });

        const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
        const summary = serious.map(
          (v) => `${v.id} (${v.impact}) x${v.nodes.length}: ${v.help}\n  e.g. ${v.nodes[0]?.target.join(" ")} ${v.nodes[0]?.failureSummary?.split("\n")[1] ?? ""}`,
        );
        expect(summary, summary.join("\n")).toEqual([]);
      });
    }
  });
}
