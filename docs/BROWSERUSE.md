# Browser Use (Chromium + Playwright)

This project now has a repeatable browser automation path for UI verification.

## What Is Available
- Playwright Node package can be installed in a temp workspace.
- Chromium binaries are installed via Playwright into:
  - `/root/.cache/ms-playwright/chromium-1161`
  - `/root/.cache/ms-playwright/chromium_headless_shell-1161`
- ffmpeg dependency for Playwright video stack is installed in:
  - `/root/.cache/ms-playwright/ffmpeg-1011`

## Quick Setup
1. Create/use temp workspace:
```bash
mkdir -p /tmp/pwverify
cd /tmp/pwverify
npm init -y
npm install playwright@1.51.1
```

2. Install browser binaries:
```bash
cd /tmp/pwverify
npx playwright install chromium
```

3. If browser launch fails with missing shared libs, install host deps:
```bash
apt-get update
apt-get install -y \
  libatk1.0-0t64 libatk-bridge2.0-0t64 libcups2t64 \
  libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
  libpango-1.0-0 libcairo2 libasound2t64 libatspi2.0-0t64
```

## Run A Script
Use Node scripts that import Playwright from `/tmp/pwverify`:
```bash
cd /tmp/pwverify
node /tmp/your_playwright_script.mjs
```

Minimal example:
```js
import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
await page.goto('https://todo.flounderboard.com/login', { waitUntil: 'domcontentloaded' });
console.log(await page.title());
await browser.close();
```

## What We Can Do
- Validate login flows and lockout UI messages.
- Validate chat UI behavior (composer, send button, error banners).
- Validate websocket UX signals visible in browser.
- Run multi-tab concurrency checks for thread-busy behavior.
- Capture screenshots for evidence.

## Practical Notes
- Use unique test users/emails per run to avoid state collisions.
- Keep browser checks separate from API checks so failures are easier to isolate.
- Run protocol checks first (`/api/health`, websocket upgrade probe) before browser checks so infra issues are separated from UI issues.
- For websocket/chat checks, backend Codex runtime availability affects results; if Codex CLI is unavailable, UI may show runtime error instead of stream output.
- Login lockout includes an IP-level key; lockout tests can unintentionally lock all subsequent logins from the same source IP during the test window.
- Backend/worker containers are expected to use host-global Codex via bind mounts (host node binary, host global node_modules, host `~/.codex` auth). If this wiring breaks, browser chat may load but turn execution can fail at runtime.

## Troubleshooting
- `ERR_MODULE_NOT_FOUND: playwright`:
  - Run scripts from `/tmp/pwverify` where `playwright` is installed.
- `ReferenceError: require is not defined in ES module scope`:
  - Use `import` in `.mjs` files, or use `.cjs` for `require(...)` syntax.
- Browser install appears to stall:
  - Wait; Playwright downloads Chromium + headless shell + ffmpeg sequentially.
- Missing Linux runtime libs warning:
  - Run the `apt-get install` command in this doc.

## Current Verification Status (2026-03-06)
- Browser runtime setup is complete: Playwright and Chromium launch successfully in headless mode.
- `/login` can be automated successfully (form fill + lockout UX assertions).
- `/chat` automation is working after frontend network-config fallback hardening (invalid `NEXT_PUBLIC_*` URL env values no longer crash chat page render).
- `browser_chat_only.cjs` currently verifies login redirect to `/chat` and composer visibility.
- When lockout is tested in the same browser run, IP-level lockout can block subsequent admin login checks; clear lockout state or separate those checks into distinct runs/contexts.

## Recommended Workflow For Future Verification
1. Run API/CLI checks first.
2. Run browser checks from `/tmp/pwverify`.
3. Log commands + key outputs in `RUN_LOG.md`.
4. Update TODO checks only for items that actually pass.
