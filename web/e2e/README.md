# End-to-end tests

Real browser, whole container stack, seeded league. Why it's built this way: `docs/Decisions/ADR-040-End-to-End-Test-Approach.md`.

```
cd web
npm run e2e:up      # builds and starts the swr-e2e stack (web http://localhost:13000), fresh database
npm run e2e         # runs every spec (set PW_CHANNEL=msedge on Windows to use the installed Edge)
npm run e2e:report  # open the HTML report
npm run e2e:down    # stop and delete the stack
```

Rebuild with `npm run e2e:up` after changing web or api code: the tests run against the built images.

| Spec | Covers |
|---|---|
| `onboarding.setup.ts` | signed-out redirect, sign-in by link, connecting Sleeper; saves the signed-in state |
| `screens.spec.ts` | every screen and state |
| `accessibility.spec.ts` | axe scan, both themes (reports in `e2e/.results/a11y`) |
| `mobile.spec.ts` | phone-sized layout and touch targets |
| `actions.spec.ts` | refresh, menu, theme, team, unfollow, sign out, delete account |
| `isolation.spec.ts` | one person cannot reach another's league |
| `pwa.spec.ts` | manifest, service worker, offline page, install card |
