import { test, expect } from '../helpers/fixtures';
import { openLogsPage } from '../helpers/app';
import { rows } from '../helpers/selectors';
import { MOCK_BACKLOG, LIVE_PUSH_ENTRY } from '../fixtures/mock-data';

/**
 * A1 (5) — live tail over SignalR.
 *
 * With no filter active the app opens a SignalR connection to the logging hub,
 * receives the backlog (GetBacklog), and appends subsequent entries (Log) live.
 * Assertions are on observable DOM + the presence of a hub connection, never on
 * the component tree.
 */
test.describe('A1 — live tail default (SignalR backlog + append)', () => {
  test('connects to the hub, shows backlog, and appends a pushed entry', async ({ page, server }) => {
    await openLogsPage(page);

    // A1 + A2: the live tail is the default view (no filter active). Proven
    // behaviourally: the hub-delivered backlog renders, which the server-search view
    // (fed by HTTP reads) does not. Its line-count copy is reference-cosmetic, so it
    // is deliberately not asserted here.
    for (const entry of MOCK_BACKLOG) {
      await expect(page.getByText(entry.Message)).toBeVisible();
    }

    // A1: the app subscribed to the logging hub.
    await expect.poll(() => server.wsConnections, {
      message: 'expected the app to open a SignalR connection to the logging hub',
    }).toBeGreaterThan(0);

    // A1: an entry pushed after connect is appended live.
    server.pushLog(LIVE_PUSH_ENTRY);
    await expect(page.getByText(LIVE_PUSH_ENTRY.Message)).toBeVisible();

    // Sanity: rows are rendering at all.
    await expect(rows(page).first()).toBeVisible();
  });
});
