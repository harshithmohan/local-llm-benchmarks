import { test, expect } from '../helpers/fixtures';
import { openLogsPage, searchValue } from '../helpers/app';
import { makeEntry } from '../fixtures/mock-data';
import {
  activeLevelChip,
  clearFiltersInView,
  levelChip,
  noResultsState,
  rows,
  scrollLockButton,
  searchInput,
  searchingState,
} from '../helpers/selectors';

/**
 * A8-A10 — server-search view states.
 *
 * A8 (4): the first in-flight fetch shows a "searching the full log history"
 *         state; a resolved-but-empty result set shows a "no results" state plus
 *         a Clear-filters action.
 * A9 (3): Clear-filters empties the search input and deactivates the chips.
 * A10 (3): the scroll-to-bottom lock is not usable while a filter is active
 *          (removed OR disabled - the ticket's "off while filters are active" reads
 *          as absent, so either state satisfies it) and is usable again in the live
 *          tail once the filters are cleared. The visible-but-disabled half of the
 *          amendment is graded in B2, not here.
 */

const READ = 'Logging/Range/Read';
const readCount = (server: { readRequests: { pathname: string }[] }) =>
  server.readRequests.filter((r) => r.pathname.endsWith(READ)).length;

test.describe('A8 — searching + no-results states', () => {
  test('shows the searching state while the first fetch is in flight', async ({ page, server }) => {
    server.setReadDelayMs(1200); // hold the response so the in-flight state is observable
    await openLogsPage(page);
    await searchInput(page).fill('error');

    // A8: the searching affordance appears before any result resolves. The status
    // hook is wording-tolerant (ticket: "a 'searching the full log history' state"),
    // so the in-flight semantics are carried by the structural check below.
    await expect(searchingState(page)).toBeVisible();
    // A8 (behavioural): while the first fetch is still held there are no result rows,
    // so the status text is what replaces the empty list.
    await expect(rows(page)).toHaveCount(0);
    // ...and once the held response lands, results replace the status.
    await expect(rows(page).first()).toBeVisible();
  });

  test('shows the no-results state and a Clear-filters action for an empty page', async ({ page, server }) => {
    server.setReadPages([{ offset: 0, NextOffset: null, Entries: [] }]);
    await openLogsPage(page);
    await searchInput(page).fill('nothing-matches-this');

    await expect.poll(() => readCount(server)).toBeGreaterThan(0);
    // A8: empty results + nothing loading -> no-results state + clear action.
    await expect(noResultsState(page)).toBeVisible();
    await expect(clearFiltersInView(page)).toBeVisible();
  });
});

test.describe('A9 — Clear filters resets search + chips', () => {
  test('clearing empties the input, deactivates chips and resumes the live tail', async ({ page, server }) => {
    // Empty result set so the in-view Clear-filters button is rendered; it triggers
    // the same reset as the toolbar button.
    server.setReadPages([{ offset: 0, NextOffset: null, Entries: [] }]);
    await openLogsPage(page);

    await levelChip(page, 'Error').click();
    await searchInput(page).fill('error');
    await expect.poll(() => readCount(server)).toBeGreaterThan(0);
    await expect(clearFiltersInView(page)).toBeVisible();

    await clearFiltersInView(page).click();

    // A9: the search text is reset...
    await expect.poll(() => searchValue(page)).toBe('');
    // ...and the level chip no longer presents as active. Tolerant chain (see
    // `activeLevelChip`): the reference exposes neither `aria-pressed` nor
    // `aria-selected`, so this resolves via its tooltip signal — active was
    // "Hide Error logs", inactive is "Show Error logs" — while an implementation that
    // does use the ARIA state still matches through that branch.
    // `toHaveCount` is unreliable on `.or()` unions, so count explicitly via poll.
    await expect.poll(() => activeLevelChip(page, 'Error').count()).toBe(0);
    // ...and still no further server reads occur.
    await page.waitForTimeout(600);
    const settled = readCount(server);
    await page.waitForTimeout(400);
    expect(readCount(server)).toBe(settled);

    // A9 (behavioural — the primary proof): clearing switched back to the live tail,
    // so a fresh hub entry renders with NO additional Range/Read request (the live
    // tail is SignalR-driven; only the server-search view issues reads).
    const resumed = makeEntry({ Message: 'harness-a9-resumed-after-clear', Level: 'Error' });
    server.pushLog(resumed);
    await expect(page.getByText(resumed.Message)).toBeVisible();
    expect(readCount(server)).toBe(settled);
  });
});

test.describe('A10 — scroll-to-bottom lock unusable while filtering', () => {
  test('lock is unusable with a filter active and usable again once cleared', async ({ page }) => {
    await openLogsPage(page);

    await levelChip(page, 'Warning').click();
    // A10: with a filter active the lock is not usable — either removed from the DOM
    // or attached but disabled. Both satisfy the ticket ("off while filters are
    // active" reads as absent), so the check accepts either state and only fails an
    // implementation that leaves the control usable. (A bare `.not.toBeEnabled()`
    // does NOT work here: a missing element reports "element(s) not found", so the
    // absent case must be probed explicitly. Whether the control is meant to STAY on
    // screen is reference polish and is graded in B2, not here.)
    await expect
      .poll(
        async () => {
          const lock = scrollLockButton(page);
          if ((await lock.count()) === 0) return 'absent';
          return (await lock.isEnabled()) ? 'enabled' : 'disabled';
        },
        { message: 'the scroll-to-bottom lock must not be usable while a filter is active' },
      )
      .not.toBe('enabled');

    // A10 (clear->usable half): once the filters are cleared the app returns to the
    // live tail and the lock is attached and enabled again — the half the previous
    // version of this spec never asserted.
    await levelChip(page, 'Warning').click();
    await expect(scrollLockButton(page)).toBeEnabled();
  });
});
