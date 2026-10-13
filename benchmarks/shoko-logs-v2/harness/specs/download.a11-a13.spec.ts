import { test, expect } from '../helpers/fixtures';
import { openLogsPage } from '../helpers/app';
import { downloadBusyIndicator, downloadButton, errorToast, levelChip, searchInput } from '../helpers/selectors';
import type { RecordedRequest } from '../helpers/mock-server';

/**
 * A11-A13 — log download.
 *
 * A11 (4): no filter -> `File/Current/Download`; any filter -> `Range/Download`.
 * A12 (4): the filtered download carries `level` + `message` params (same singular
 *          / omitted-when-empty rules as A5).
 * A13 (3): the download control shows a busy state while in flight; a failed
 *          download surfaces an error toast.
 */

const CURRENT = 'Logging/File/Current/Download';
const RANGE_DL = 'Logging/Range/Download';

const downloads = (server: { downloadRequests: RecordedRequest[] }, suffix: string) =>
  server.downloadRequests.filter((r) => r.pathname.endsWith(suffix));

test.describe('A11/A12 — download endpoint selection + params', () => {
  test('unfiltered download hits File/Current/Download', async ({ page, server }) => {
    await openLogsPage(page);
    await downloadButton(page).click();

    await expect.poll(() => downloads(server, CURRENT).length).toBeGreaterThan(0);
    expect(downloads(server, RANGE_DL).length).toBe(0);
  });

  test('a chip routes download to Range/Download and sends level', async ({ page, server }) => {
    await openLogsPage(page);
    await levelChip(page, 'Trace').click();
    await downloadButton(page).click();

    await expect.poll(() => downloads(server, RANGE_DL).length).toBeGreaterThan(0);
    expect(downloads(server, CURRENT).length).toBe(0);

    // A12
    const req = downloads(server, RANGE_DL).at(-1)!;
    expect(req.query.level).toContain('Trace');
    expect(req.has('levels')).toBe(false); // singular only
    expect(req.has('message')).toBe(false); // omitted when there is no search text
  });

  test('an active search adds the message param to the ranged download', async ({ page, server }) => {
    await openLogsPage(page);
    await searchInput(page).fill('metadata');
    await expect.poll(() => server.readRequests.length).toBeGreaterThan(0); // search debounced
    await downloadButton(page).click();

    await expect.poll(() => downloads(server, RANGE_DL).length).toBeGreaterThan(0);
    const req = downloads(server, RANGE_DL).at(-1)!;
    expect(req.query.message).toContain('metadata');
  });
});

test.describe('A13 — busy state + error toast', () => {
  test('the download control is busy while in flight and errors surface a toast', async ({ page, server }) => {
    await openLogsPage(page);
    server.setDownload({ delayMs: 1500 });

    const button = downloadButton(page);
    await button.click();

    // A13: busy while in flight — the control disables itself (`loading` sets the
    // button's `disabled` attribute)...
    await expect(button).toBeDisabled();
    // ...and shows a VISIBLE busy affordance (the `disabled` attribute alone is not a
    // visible indicator). Tolerant chain (see `downloadBusyIndicator`): `aria-busy`,
    // a `data-loading` marker, or the reference's overlaid spinner SVG inside it.
    await expect(downloadBusyIndicator(page).first()).toBeVisible();
    // A13: the affordance is gone once the request settles (this first download
    // succeeds, so the button returns to its idle, enabled state). `.first()` +
    // `toBeHidden()` (rather than `toHaveCount`) keeps the assertion stable across
    // both the multi-match CSS list and any candidate's own affordance shape — an
    // empty match set resolves `.first()` to nothing, which `toBeHidden()` treats as
    // hidden, while a present spinner is visible.
    await expect(downloadBusyIndicator(page).first()).toBeHidden({ timeout: 10_000 });
    await expect(button).toBeEnabled();

    // A13: a failed download surfaces an error toast.
    server.setDownload({ status: 500 });
    await button.click();
    await expect(errorToast(page)).toBeVisible({ timeout: 10_000 });
  });
});
