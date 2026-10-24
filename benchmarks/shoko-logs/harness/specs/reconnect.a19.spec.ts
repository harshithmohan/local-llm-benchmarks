import { test, expect } from '../helpers/fixtures';
import { openLogsPage } from '../helpers/app';
import { rows } from '../helpers/selectors';
import {
  LIVE_PUSH_ENTRY,
  MOCK_BACKLOG,
  MOCK_RECONNECT_BACKLOG,
  POST_RECONNECT_ENTRY,
  RECONNECT_DOWN_ENTRY,
} from '../fixtures/mock-data';

/**
 * A19 (8) — reconnect recovery (runtime).
 *
 * The server replays `GetBacklog` on EVERY connect, so after a SignalR reconnect the
 * app must RESET the tail before appending the fresh backlog: the fresh entries
 * replace the now-stale pre-disconnect entries (no stale entries stranded above the
 * fresh set) and entries that arrive after the reconnect are still appended. The
 * reference does this in `onreconnected` (`queryClient.setQueryData(['logs'], [])`),
 * with the replayed `GetBacklog` appended right after. Any race-free ordering is
 * accepted; this asserts observable DOM only.
 *
 * The forced reconnect uses the reference's retry policy (`withAutomaticReconnect`
 * starts at 5 s), so the budget below is generous.
 */
test.describe('A19 — reconnect replaces the stale tail with the fresh backlog', () => {
  test('fresh backlog replaces stale entries and post-reconnect entries still append', async ({ page, server }) => {
    await openLogsPage(page);

    // Precondition: the initial live tail rendered the connect backlog.
    for (const entry of MOCK_BACKLOG) {
      await expect(page.getByText(entry.Message)).toBeVisible();
    }

    // The next handshake (the reconnect) replays a DIFFERENT backlog.
    server.setBacklog(MOCK_RECONNECT_BACKLOG);

    // Drop the logging socket so the app runs its automatic-reconnect path.
    await server.dropLoggingSockets();

    // A19: the fresh backlog is rendered after the reconnect (first retry is 5 s).
    await expect(page.getByText(MOCK_RECONNECT_BACKLOG[0].Message)).toBeVisible({ timeout: 20_000 });
    for (const entry of MOCK_RECONNECT_BACKLOG) {
      await expect(page.getByText(entry.Message)).toBeVisible();
    }

    // A19: stale pre-disconnect entries are gone — not stranded above the fresh set.
    for (const entry of MOCK_BACKLOG) {
      await expect(page.getByText(entry.Message)).toHaveCount(0);
    }

    // A19: the fresh backlog is not duplicated (reset-then-append, not append-only).
    for (const entry of MOCK_RECONNECT_BACKLOG) {
      await expect(page.getByText(entry.Message)).toHaveCount(1);
    }

    // A19: the live append path still works after the reset.
    server.pushLog(POST_RECONNECT_ENTRY);
    await expect(page.getByText(POST_RECONNECT_ENTRY.Message)).toBeVisible();

    // Sanity: rows are rendering at all.
    await expect(rows(page).first()).toBeVisible();
  });

  test('a log arriving during the reconnect reset/replay window is not dropped', async ({ page, server }) => {
    await openLogsPage(page);

    // Precondition: the initial live tail rendered the connect backlog.
    for (const entry of MOCK_BACKLOG) {
      await expect(page.getByText(entry.Message)).toBeVisible();
    }

    // Hold the NEXT logging-hub backlog replay so we can inject logs during the
    // reconnect window, BEFORE the fresh backlog is delivered.
    server.holdBacklogReplay();

    // The reconnect handshake will replay a DIFFERENT backlog.
    server.setBacklog(MOCK_RECONNECT_BACKLOG);

    // Drop the logging socket so the app runs its automatic-reconnect path.
    await server.dropLoggingSockets();

    // WINDOW A — the socket is DOWN. An entry pushed now is retained by the server's
    // backlog and must be delivered by the reconnect replay, not lost.
    server.pushLog(RECONNECT_DOWN_ENTRY);

    // WINDOW B — the socket is UP but the replay is still held. Wait until the NEW
    // logging socket has completed its SignalR handshake (the stub has answered it)
    // while the replay gate is still held, so the next push is a genuine LIVE
    // delivery racing the held replay — not merely a backlog entry retained while
    // the socket was down (which the previous version of this test only proved).
    await expect.poll(() => server.loggingHandshakes, { timeout: 20_000 }).toBeGreaterThanOrEqual(2);

    // A genuine live delivery on the OPEN reconnect socket, racing the held replay.
    server.pushLog(POST_RECONNECT_ENTRY);

    // Release the held replay: the reconnect handshake now delivers the backlog,
    // which must include the entry queued while the socket was down.
    server.releaseBacklogReplay();

    // (i) every fresh entry renders after the reconnect (first retry is 5 s).
    await expect(page.getByText(MOCK_RECONNECT_BACKLOG[0].Message)).toBeVisible({ timeout: 20_000 });
    for (const entry of MOCK_RECONNECT_BACKLOG) {
      await expect(page.getByText(entry.Message)).toBeVisible();
    }

    // (ii) the stale pre-disconnect entries are gone — not stranded above the fresh set.
    for (const entry of MOCK_BACKLOG) {
      await expect(page.getByText(entry.Message)).toHaveCount(0);
    }

    // (iii) the fresh backlog is not duplicated (reset-then-append, not append-only).
    for (const entry of MOCK_RECONNECT_BACKLOG) {
      await expect(page.getByText(entry.Message)).toHaveCount(1);
    }

    // (iv) BOTH race windows render exactly once — the entry queued while the socket
    // was down is delivered by the replay, and the entry delivered live while the
    // replay was held is neither dropped by the reset nor duplicated by it.
    await expect(page.getByText(RECONNECT_DOWN_ENTRY.Message)).toHaveCount(1);
    await expect(page.getByText(POST_RECONNECT_ENTRY.Message)).toHaveCount(1);

    // (v) the live append path still works after the reset.
    server.pushLog(LIVE_PUSH_ENTRY);
    await expect(page.getByText(LIVE_PUSH_ENTRY.Message)).toBeVisible();

    // Sanity: rows are rendering at all.
    await expect(rows(page).first()).toBeVisible();
  });
});
