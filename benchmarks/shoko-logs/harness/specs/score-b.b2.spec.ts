import { test, expect } from '../helpers/fixtures';
import {
  expectEntryInListViewport,
  expectEntryNotInListViewport,
  expectListAtBottom,
  expectListNotAtBottom,
  listScrollState,
  openLogsPage,
  scrollListToBottomProgrammatically,
  settledListScrollState,
  wheelList,
} from '../helpers/app';
import { makeEntry, type MockEntry } from '../fixtures/mock-data';
import { levelChip, scrollLockButton } from '../helpers/selectors';

/**
 * B2 (11) — scroll lock (behavioural).
 *
 * The live tail auto-follows new entries: the newest entry is kept in view at the
 * bottom of the list. A GENUINE user scroll-up (a real wheel over the list) releases
 * that follow, and it must stay released through the app's own programmatic scrolling
 * (`scrollToIndex`) and the virtualizer's measurement corrections — those carry no
 * user intent, so they may neither release the follow nor silently re-engage it.
 *
 * These specs grade the OUTCOME the rubric states, never the reference's mechanism
 * (the rubric is explicit that "the bottom-distance check is one valid mechanism"):
 * the tail's scroll geometry is read live and the assertions are "is the newest
 * entry inside the visible area" and "did the viewport stay where the user left it".
 *
 * Reference note: the reference releases the follow only on a user scroll and only
 * ever re-engages it via the lock toggle — it does NOT re-lock when the user scrolls
 * back down to the bottom, so no re-lock assertion is made (rubric: assert it only
 * if the reference does it).
 */

/** A long backlog so the virtualized list is genuinely scrollable at the 1280x1200 viewport. */
const BULK_BACKLOG: MockEntry[] = Array.from({ length: 200 }, (_, index) =>
  makeEntry({
    Message: `harness-b2-bulk-${String(index).padStart(3, '0')} filler line for scrolling`,
    Level: index % 3 === 0 ? 'Warning' : 'Information',
  }),
);

const pushed = (message: string): MockEntry => makeEntry({ Message: message, Level: 'Error' });

test.describe('B2 — scroll lock (behavioural)', () => {
  test.beforeEach(async ({ server }) => {
    server.setBacklog(BULK_BACKLOG);
  });

  test('the tail follows new entries, keeping the newest at the bottom', async ({ page, server }) => {
    await openLogsPage(page);
    await expectListAtBottom(page, 'the tail should be scrolled to the bottom once the backlog renders');

    const entry = pushed('harness-b2-follow-1');
    server.pushLog(entry);

    await expect(page.getByText(entry.Message)).toBeVisible();
    await expectListAtBottom(page, 'a new entry should keep the tail pinned to the bottom');
    await expectEntryInListViewport(page, entry.Message);
  });

  test('stays following through a programmatic scroll (scrollToIndex + measurement)', async ({ page, server }) => {
    await openLogsPage(page);
    await expectListAtBottom(page);

    // A programmatic jump to the end is exactly what the app itself does to follow;
    // the scroll event it fires is what a measurement correction emits.
    await scrollListToBottomProgrammatically(page);

    const entry = pushed('harness-b2-follow-2');
    server.pushLog(entry);

    await expect(page.getByText(entry.Message)).toBeVisible();
    await expectListAtBottom(page, 'a programmatic scroll must not release the follow');
    await expectEntryInListViewport(page, entry.Message);
  });

  test('a genuine user wheel-up releases the follow', async ({ page, server }) => {
    await openLogsPage(page);
    await expectListAtBottom(page);

    await wheelList(page, -800);
    await expectListNotAtBottom(page, 'a genuine user scroll-up should release the follow');

    const before = await settledListScrollState(page);
    const entry = pushed('harness-b2-release-1');
    server.pushLog(entry);

    // The append is processed (the list grows) but the viewport is NOT yanked back:
    // polling the bottom gap asserts it settles (and stays) away from the bottom.
    await expect
      .poll(async () => (await listScrollState(page)).scrollHeight, {
        message: 'expected the pushed entry to be appended to the list',
      })
      .toBeGreaterThan(before.scrollHeight);
    await expectListNotAtBottom(page, 'the released follow must not scroll the viewport back to the bottom');

    const after = await listScrollState(page);
    expect(after.scrollTop, 'the viewport must stay where the user left it').toBeLessThanOrEqual(
      before.scrollTop + 1,
    );
    await expectEntryNotInListViewport(page, entry.Message);
  });

  test('programmatic scrolling does not re-engage a released follow', async ({ page, server }) => {
    await openLogsPage(page);
    await expectListAtBottom(page);

    await wheelList(page, -800);
    await expectListNotAtBottom(page);

    // Landing back at the bottom without user intent (a virtualizer / scrollToIndex
    // correction) must not silently re-engage the follow.
    await scrollListToBottomProgrammatically(page);
    await expectListAtBottom(page, 'the programmatic scroll itself should land at the bottom');

    const before = await settledListScrollState(page);
    const entry = pushed('harness-b2-programmatic-1');
    server.pushLog(entry);

    await expect
      .poll(async () => (await listScrollState(page)).scrollHeight, {
        message: 'expected the pushed entry to be appended to the list',
      })
      .toBeGreaterThan(before.scrollHeight);
    await expectListNotAtBottom(page, 'a released follow must not be re-engaged by a programmatic scroll');

    const after = await listScrollState(page);
    expect(after.scrollTop, 'the viewport must not follow the new entry').toBeLessThanOrEqual(
      before.scrollTop + 1,
    );
  });

  test('the lock control stays visible but unusable while a filter is active', async ({ page }) => {
    await openLogsPage(page);

    await levelChip(page, 'Warning').click();

    // B2 (visible-but-unusable): while a filter is active the control stays on screen
    // and merely disables — removing it from the DOM is the wrong answer. Asserting
    // visibility FIRST is what makes this non-vacuous: an implementation that hides
    // the control fails here instead of passing on a disabled-but-absent query.
    const lock = scrollLockButton(page);
    await expect(lock).toBeVisible();
    await expect(lock).toBeDisabled();
  });
});
