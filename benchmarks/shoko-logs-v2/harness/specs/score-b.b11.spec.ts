import { test, expect } from '../helpers/fixtures';
import { openLogsPage } from '../helpers/app';
import { searchInput } from '../helpers/selectors';
import type { RecordedRequest } from '../helpers/mock-server';

/**
 * B11 (7) — search-input discipline (behavioural).
 *
 * The rubric line is deliberately NARROW: debounce means rapid typing COALESCES
 * into a single request carrying the FINAL value, and the value sent is TRIMMED.
 * The debounce INTERVAL is not pinned — the codebase's own search inputs vary — so
 * the assertions are behavioural ("no request fires per keystroke"; "exactly one
 * settled request carrying the final value"; "the sent value is trimmed") and never
 * encode a millisecond figure. Any debounce interval passes so long as it coalesces
 * and trims.
 *
 * The reference wraps plain text as `c#:<text>` (a DSL prefix, `toServerSearch`); a
 * bare literal is equally acceptable, so every value assertion accepts either form
 * and rejects anything else — an intermediate keystroke prefix, a superset, or
 * untrimmed surrounding whitespace.
 */

const READ = 'Logging/Range/Read';

const readRequests = (server: { readRequests: RecordedRequest[] }) =>
  server.readRequests.filter((r) => r.pathname.endsWith(READ));

/** The settled value: the reference's `c#:`-wrapped form, or a bare literal. */
const settled = (value: string) => new RegExp(`^(c#:)?${value}$`);

test.describe('B11 — search-input discipline (7 pts, behavioural)', () => {
  test('rapid keystrokes coalesce into a single read (not one request per keystroke)', async ({ page, server }) => {
    await openLogsPage(page);
    const input = searchInput(page);

    await input.fill('e');
    await input.fill('er');
    await input.fill('err');

    // (a) No request fires per keystroke. A synchronous per-keystroke send would
    // land within this short LOWER-bound window; any real debounce (at ANY interval)
    // fires later. This is a lower bound only — it never requires a read to have
    // fired, so it cannot fail a slower debounce, and it pins no interval.
    await page.waitForTimeout(120);
    expect(readRequests(server).length).toBe(0);

    // Coalesced: three keystrokes settle into EXACTLY ONE read. Polled with a
    // generous timeout (never a fixed sleep), so wall-clock jitter cannot flake it.
    await expect.poll(() => readRequests(server).length, { timeout: 5000 }).toBe(1);
  });

  test('the value sent is the settled final value (no intermediate keystroke, no superset)', async ({ page, server }) => {
    await openLogsPage(page);
    const input = searchInput(page);

    await input.fill('e');
    await input.fill('er');
    await input.fill('err');

    // (b) Exactly ONE settled request — polled with a generous timeout, never a fixed
    // sleep, and never asserting a specific debounce interval.
    await expect.poll(() => readRequests(server).length, { timeout: 5000 }).toBe(1);

    // ...and it carries exactly the final value: `c#:err` or `err`. The anchored
    // match rejects an intermediate keystroke prefix (`c#:e`, `c#:er`) and any
    // superset (`c#:error`, `c#:xerrx`).
    const message = readRequests(server).at(-1)?.query.message ?? '';
    expect(message, 'the settled read must carry only the final value').toMatch(settled('err'));
  });

  test('the search text is sent trimmed', async ({ page, server }) => {
    await openLogsPage(page);
    await searchInput(page).fill('  err  ');

    await expect.poll(() => readRequests(server).length, { timeout: 5000 }).toBeGreaterThan(0);
    const message = server.lastRead()?.query.message ?? '';
    // (c) Exactly `c#:err` or `err` — no leading/trailing whitespace survives.
    expect(message, 'the sent value must be exactly the trimmed term').toMatch(settled('err'));
  });
});
