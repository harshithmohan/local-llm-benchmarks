import { test, expect } from '../helpers/fixtures';
import { expectLiveTail, openLogsPage } from '../helpers/app';
import { levelChip, searchInput } from '../helpers/selectors';
import type { RecordedRequest } from '../helpers/mock-server';

/**
 * A2–A5 — the server-search contract.
 *
 * A2 (5): any active filter (non-empty debounced search OR >=1 chip) switches to
 *          the server-search view; clearing switches back to the live tail.
 * A3 (2):  empty or blank input is not a search filter (the view stays on the live
 *          tail). The debounce/trim behaviour is NOT part of the ticket — it is
 *          graded behaviourally in Score B (B11, specs/score-b.b11.spec.ts).
 * A4 (4):  level chips filter SERVER-side — every read carries a `level` param.
 * A5 (6): the read request uses `level` (singular), `message`, `offset`, `limit`,
 *          `descending=false`; empty `level`/`message` are OMITTED (never empty strings).
 *
 * The reference UI sends `level` as a comma-joined list of active level names and
 * `message` as the (trimmed) search text, sometimes DSL-wrapped as `c#:<text>`.
 * Assertions below tolerate the DSL wrapper but require the substring to be present.
 */

const READ = 'Logging/Range/Read';

const readRequests = (server: { readRequests: RecordedRequest[] }) =>
  server.readRequests.filter((r) => r.pathname.endsWith(READ));

test.describe('A2 — activating a filter switches views', () => {
  test('search text switches to the server-search view; clearing returns to live tail', async ({ page, server }) => {
    await openLogsPage(page);
    await expectLiveTail(page);

    await searchInput(page).fill('error');

    // A2: a server read is issued once the search is active.
    await expect.poll(() => readRequests(server).length).toBeGreaterThan(0);

    // A2: clearing the text returns to the live tail and stops issuing reads.
    await searchInput(page).fill('');
    await expect.poll(() => readRequests(server).length, { timeout: 5000 }).toBeGreaterThan(0);
    const afterClear = readRequests(server).length;
    await page.waitForTimeout(600);
    expect(readRequests(server).length).toBe(afterClear); // no new read while unfiltered
    await expectLiveTail(page);
  });

  test('a level chip alone switches to the server-search view', async ({ page, server }) => {
    await openLogsPage(page);
    await levelChip(page, 'Error').click();

    // A2 + A4: an active chip alone issues a filtered server read.
    await expect.poll(() => readRequests(server).length).toBeGreaterThan(0);
    expect(server.lastRead()?.query.level).toBeTruthy();
  });
});

test.describe('A3 — empty/blank input is not a filter (2 pts, [R])', () => {
  test('whitespace-only input is not a filter (no read, still live)', async ({ page, server }) => {
    await openLogsPage(page);
    await searchInput(page).fill('    ');

    await page.waitForTimeout(600);
    expect(readRequests(server).length).toBe(0);
    await expectLiveTail(page);
  });
});

test.describe('A4 — chips filter server-side', () => {
  test('every read carries a level param while a chip is active', async ({ page, server }) => {
    await openLogsPage(page);

    // A4: the ticket names the roster — Trace, Debug, Information, Warning, Error,
    // Critical. A level with no chip at all is a conformance failure, and a two-chip
    // click cannot detect a missing sixth, so the roster is asserted explicitly.
    for (const level of ['Trace', 'Debug', 'Information', 'Warning', 'Error', 'Critical']) {
      await expect(levelChip(page, level), `${level} chip is present`).toHaveCount(1);
    }

    await levelChip(page, 'Trace').click();
    await levelChip(page, 'Error').click();

    await expect.poll(() => readRequests(server).length).toBeGreaterThan(0);
    await page.waitForTimeout(400);

    // A4: no read may omit `level` (that would mean a full unfiltered fetch that
    // the client then filtered locally).
    for (const req of readRequests(server)) {
      expect(req.query.level, `read ${req.url} must carry a level filter`).toBeTruthy();
    }
    const levels = (server.lastRead()?.query.level ?? '')
      .split(',')
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean);
    expect(new Set(levels)).toEqual(new Set(['trace', 'error']));
  });
});

test.describe('A5 — Range/Read parameter contract', () => {
  test('uses singular level, message, offset, limit and descending=false; omits empties', async ({ page, server }) => {
    await openLogsPage(page);

    // Chip only: level present, message OMITTED (not empty string).
    await levelChip(page, 'Warning').click();
    await expect.poll(() => readRequests(server).length).toBeGreaterThan(0);
    const chipOnly = server.lastRead()!;
    expect(chipOnly.pathname.endsWith(READ)).toBeTruthy();
    expect(chipOnly.query.level).toBeTruthy();
    expect(chipOnly.query.offset).toBeDefined();
    expect(chipOnly.query.limit).toBeDefined();
    expect(chipOnly.query.descending).toBe('false');
    expect(chipOnly.has('levels')).toBe(false); // singular only
    expect(chipOnly.has('message')).toBe(false); // omitted when there is no search text

    // Text only: message present, level OMITTED.
    await levelChip(page, 'Warning').click(); // toggle the chip back off
    await searchInput(page).fill('metadata');
    await expect.poll(() => readRequests(server).length).toBeGreaterThan(1);
    const textOnly = server.lastRead()!;
    expect(textOnly.query.message).toContain('metadata');
    expect(textOnly.has('level')).toBe(false);
    expect(textOnly.query.descending).toBe('false');
  });
});
