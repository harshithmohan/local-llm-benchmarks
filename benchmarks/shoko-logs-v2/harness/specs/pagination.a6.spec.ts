import { test, expect } from '../helpers/fixtures';
import { openLogsPage } from '../helpers/app';
import { levelChip, rows, scrollSearchToEnd } from '../helpers/selectors';
import { DEFAULT_READ_PAGES } from '../fixtures/mock-data';

/**
 * A6 (7) — cursor-driven pagination in the server-search view.
 *
 * On a server-search (a chip is enough to activate it), the first read uses
 * offset=0; scrolling toward the end auto-fetches the next page with
 * offset === the previous response's NextOffset; a `NextOffset: null` stops paging.
 * A rubric score of 0 here means no next-page fetch ever happens.
 *
 * A7 (5) — result rendering: the fetched pages concatenate in ascending order with
 * no dropped or duplicated entries, and each rendered row exposes the entry's
 * timestamp, level and message from the returned fields. This proves the
 * concatenation is lossless and ordered, and that rows carry the server-returned
 * fields rather than placeholder text.
 */

const READ = 'Logging/Range/Read';
const PAGE_1_ENTRY = DEFAULT_READ_PAGES[0].Entries[0].Message;
const PAGE_2_ENTRY = DEFAULT_READ_PAGES[1].Entries[0].Message;

test.describe('A6 — scroll-driven pagination via NextOffset', () => {
  test('fetches the next page with offset === previous NextOffset, then stops at null', async ({ page, server }) => {
    // Opt into a two-page result set (the mock's default first page is terminal).
    server.setReadPages(DEFAULT_READ_PAGES);
    await openLogsPage(page);
    // A chip activates the server-search view without needing debounce timing.
    await levelChip(page, 'Information').click();

    // First page: offset 0.
    await expect.poll(() => server.readRequests.length).toBeGreaterThan(0);
    const first = server.readRequests[0];
    expect(first.query.offset).toBe('0');
    await expect(page.getByText(PAGE_1_ENTRY)).toBeVisible();

    // Scroll toward the end -> next page must be requested with offset=100 (the
    // NextOffset the stub returned for page 1).
    await scrollSearchToEnd(page);
    await expect.poll(() => server.readRequests.length, {
      message: 'expected a next-page fetch after scrolling to the end',
      timeout: 10_000,
    }).toBeGreaterThan(1);
    const second = server.readRequests[1];
    expect(Number(second.query.offset)).toBe(DEFAULT_READ_PAGES[0].NextOffset);
    await expect(page.getByText(PAGE_2_ENTRY)).toBeVisible();

    // Page 2 returned NextOffset: null -> further scrolling must NOT fetch again.
    const before = server.readRequests.length;
    await scrollSearchToEnd(page);
    await page.waitForTimeout(800);
    expect(server.readRequests.length).toBe(before);
  });

  test('stops immediately when the first page reports NextOffset null', async ({ page, server }) => {
    server.setReadPages([
      { offset: 0, NextOffset: null, Entries: DEFAULT_READ_PAGES[0].Entries },
    ]);
    await openLogsPage(page);
    await levelChip(page, 'Information').click();

    await expect.poll(() => server.readRequests.length).toBeGreaterThan(0);
    const before = server.readRequests.length;
    await scrollSearchToEnd(page);
    await page.waitForTimeout(800);
    expect(server.readRequests.length).toBe(before);
  });

  test('A7: both fetched pages concatenate in order, with no dropped or duplicated rows', async ({ page, server }) => {
    // Two-page result set: page 1 (offset 0) -> page 2 (offset 100), terminal.
    server.setReadPages(DEFAULT_READ_PAGES);
    await openLogsPage(page);
    await levelChip(page, 'Information').click();

    // First page renders...
    await expect(page.getByText(PAGE_1_ENTRY)).toBeVisible();
    // ...and scrolling pulls the second page in.
    await scrollSearchToEnd(page);
    await expect(page.getByText(PAGE_2_ENTRY)).toBeVisible();

    // The union of both fetched pages, in ascending (page 1 then page 2) order.
    const allEntries = [...DEFAULT_READ_PAGES[0].Entries, ...DEFAULT_READ_PAGES[1].Entries];
    const expectedMessages = allEntries.map((entry) => entry.Message);

    // The whole (four-row) result set fits the viewport, so every fetched entry is
    // mounted: assert the exact row count first (no dropped, no duplicated rows).
    await expect(rows(page)).toHaveCount(expectedMessages.length);

    const rowTexts = await rows(page).allTextContents();

    // Every fetched entry renders exactly once...
    for (const message of expectedMessages) {
      expect(
        rowTexts.filter((text) => text.includes(message)),
        `"${message}" must render exactly once`,
      ).toHaveLength(1);
    }

    // ...and the rows concatenate in ascending order (page 1 before page 2).
    const renderedOrder = rowTexts.map((text) => expectedMessages.findIndex((m) => text.includes(m)));
    expect(renderedOrder, 'rows must render in ascending fetched order').toEqual(
      expectedMessages.map((_, index) => index),
    );

    // Each row exposes the entry's timestamp, level and message from the returned fields.
    for (const entry of allEntries) {
      const row = rows(page).filter({ hasText: entry.Message });
      await expect(row, `row for "${entry.Message}"`).toHaveCount(1);
      const text = (await row.textContent()) ?? '';
      expect(text, `"${entry.Message}" row must show a timestamp`).toMatch(
        /\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}/,
      );
      expect(text, `"${entry.Message}" row must show its level`).toContain(entry.Level);
      expect(text).toContain(entry.Message);
    }
  });
});
