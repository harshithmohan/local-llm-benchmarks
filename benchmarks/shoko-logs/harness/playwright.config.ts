import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright config for the shoko-logs runtime acceptance harness.
 *
 * The candidate checkout is taken from SHOKO_WEBUI_DIR and never hard-coded.
 * Playwright's `webServer` boots the checkout's Vite dev server (via
 * scripts/dev-server.mjs, which forces `server.open` off) and tears it down when
 * the run ends. The dev server is served at `/webui/` (the app's Vite `base`).
 */

const webuiDir = process.env.SHOKO_WEBUI_DIR;
if (!webuiDir) {
  throw new Error(
    'SHOKO_WEBUI_DIR is not set. Point it at the Shoko-WebUI checkout, e.g.\n' +
      '  SHOKO_WEBUI_DIR=/path/to/Shoko-WebUI npx playwright test',
  );
}

const port = Number(process.env.HARNESS_PORT ?? 3100);
const baseURL = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: './specs',
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0,
  // Per-test budget. A passing test resolves in ~2 s, but Playwright can only
  // conclude a FAILING test by exhausting this budget (auto-waiting cannot tell
  // "broken" from "slow"), so a candidate that breaks N specs costs ~N x this.
  // Kept far above the slowest reference test (a few seconds) so a conformant
  // candidate can never time out here.
  timeout: 30_000,
  expect: { timeout: 10_000 },
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: 'playwright-report' }],
    // Sanitized failure report for the reviewer (spec/test titles + symptoms
    // only, no selector internals). Written to HARNESS_REPORT, else
    // ./harness-report.md. See reporters/sanitized-report.ts.
    ['./reporters/sanitized-report.ts', {}],
  ],
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    // Tall viewport so the virtualized search list renders its trailing loader
    // row in a single scroll (A6) without extra scrolling gymnastics.
    viewport: { width: 1280, height: 1200 },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 1200 } },
    },
  ],
  webServer: {
    // scripts/dev-server.mjs resolves Vite from the CHECKOUT's node_modules and
    // starts it on HARNESS_PORT with `server.open` disabled.
    command: 'node scripts/dev-server.mjs',
    url: `${baseURL}/webui/`,
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
    stdout: 'pipe',
    stderr: 'pipe',
    env: {
      SHOKO_WEBUI_DIR: webuiDir,
      HARNESS_PORT: String(port),
    },
  },
});
