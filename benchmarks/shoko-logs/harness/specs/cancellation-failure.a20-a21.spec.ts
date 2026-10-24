import { test, expect } from '../helpers/fixtures';
import { openLogsPage } from '../helpers/app';
import { errorAffordance, rows, searchInput } from '../helpers/selectors';
import { SEARCH_PAGE_1, SEARCH_PAGE_2 } from '../fixtures/mock-data';

/**
 * A20 (6) — cancellation: changing the filters ignores the in-flight read.
 *
 * A slow first read (filter "alpha") is left in flight while the filter changes to
 * "beta", whose read returns a different page set immediately. The newer results
 * must render, and the stale set's distinct marker must never render - not even
 * after the slow response finally arrives. This proves the view keys results to the
 * active filters instead of letting a stale response paint over newer results.
 *
 * A21 (3) — failure surfacing: a failed read shows a visible error state.
 *
 * A read that fails must surface a visible error affordance rather than failing
 * silently or reading as the empty-results state. The reference raises an error
 * toast (and may also show the empty state); the assertion requires the visible
 * error affordance, which is what distinguishes a failure from "no results".
 */

test.describe('A20 — stale in-flight reads / A21 — failure surfacing', () => {
  test('A20: a stale in-flight read never renders over the newer filter results', async ({ page, server }) => {
    const stale = SEARCH_PAGE_1; // slow (read #1) response set
    const fresh = SEARCH_PAGE_2; // fast (read #2) response set

    // Read #1: filter "alpha", served slowly with the stale page set.
    server.setReadPages([{ offset: 0, NextOffset: null, Entries: stale }]);
    server.setReadDelayMs(2_500);
    await openLogsPage(page);
    await searchInput(page).fill('alpha');
    await expect.poll(() => server.readRequests.length).toBeGreaterThan(0);

    // While read #1 is still sleeping, switch the filter to "beta"; read #2 is
    // served immediately with the fresh page set.
    server.setReadDelayMs(0);
    server.setReadPages([{ offset: 0, NextOffset: null, Entries: fresh }]);
    await searchInput(page).fill('beta');
    await expect(page.getByText(fresh[0].Message)).toBeVisible();
    await expect.poll(() => server.readRequests.length).toBeGreaterThan(1);

    // Restore the stale set so the still-sleeping read #1 genuinely resolves with it.
    server.setReadPages([{ offset: 0, NextOffset: null, Entries: stale }]);

    // Wait past read #1's delay so its stale response has arrived and been handled.
    await page.waitForTimeout(3_200);

    // The rendered rows must be the fresh set only: the stale response never paints.
    const rendered = (await rows(page).allTextContents()).join('\n');
    expect(rendered, 'the stale read result must not render').not.toContain(stale[0].Message);
    expect(rendered, 'the newer filter results must still be rendered').toContain(fresh[0].Message);
  });

  test('A21: a failed read surfaces a visible error state, not a silent empty state', async ({ page, server }) => {
    await openLogsPage(page);

    // Fail the read, then trigger one.
    server.setReadError(400);
    await searchInput(page).fill('boom');

    // A visible error affordance must appear. The empty-results state alone is not a
    // failure signal, so require the distinct error affordance: the reference's toast,
    // or an inline failure banner (the download's toast belongs to A13, not this line).
    await expect(errorAffordance(page)).toBeVisible();
    await expect(errorAffordance(page)).toContainText(/failed|failure|could not|unable to|went wrong|error/i);
  });
});
