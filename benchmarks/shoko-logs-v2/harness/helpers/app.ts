import { expect, type Page } from '@playwright/test';
import { logsHeading, searchInput } from './selectors';
import { MOCK_BACKLOG } from '../fixtures/mock-data';

/** The logs route (the app is served under Vite `base: "/webui/"`). */
export const LOGS_PATH = '/webui/log';

/** Seeded API key — the value is unimportant; presence authenticates the session. */
export const TEST_APIKEY = 'harness-apikey';

/**
 * Seed the app's persisted session so AuthenticatedRoute does not redirect to
 * login. The app's loadState() accepts `localStorage.apiSession` when it carries
 * a truthy `version`, so we write exactly that before any page script runs.
 */
export async function seedAuth(page: Page): Promise<void> {
  await page.addInitScript((apikey: string) => {
    try {
      globalThis.localStorage.setItem(
        'apiSession',
        JSON.stringify({ apikey, username: 'admin', rememberUser: true, version: 'harness' }),
      );
    } catch {
      /* storage unavailable — the test will fail loudly at the auth gate */
    }
  }, TEST_APIKEY);
}

/** Navigate to the logs page and wait until it has rendered. */
export async function openLogsPage(page: Page): Promise<void> {
  await page.goto(LOGS_PATH);
  await expect(logsHeading(page)).toBeVisible();
}

/**
 * Assert the DEFAULT, unfiltered live tail is showing (not the server-search view).
 *
 * The reference labels this view "<n> lines in the live tail", but that count line is
 * reference-cosmetic: the ticket only requires the existing live tail to keep working
 * ("backlog delivered on connect plus new entries appended as they arrive",
 * `prompt.md:55-56`) and never pins that string, so asserting it would fail a
 * conformant candidate that worded it differently. Prove the view behaviourally
 * instead: the entries the stub delivered over the SignalR hub are rendered. The
 * server-search view renders HTTP read results instead, so these texts are unique to
 * the live tail - their presence means the app is on the unfiltered live view.
 */
export async function expectLiveTail(page: Page): Promise<void> {
  for (const entry of MOCK_BACKLOG) {
    await expect(
      page.getByText(entry.Message),
      'the hub-delivered backlog should render in the default live tail',
    ).toBeVisible();
  }
}

/** Read the current value of the search input. */
export async function searchValue(page: Page): Promise<string> {
  return searchInput(page).inputValue();
}

/* -------------------------------------------------------------------------- */
/* Scroll-lock helpers (B2)                                                    */
/* -------------------------------------------------------------------------- */

/**
 * The live tail is a virtualized (`@tanstack/react-virtual`) scroll container. The
 * ticket pins no markup for it, so the container is discovered STRUCTURALLY — the
 * nearest scrollable ancestor of a rendered row — exactly as `scrollSearchToEnd`
 * does, and every helper below reads live geometry rather than class names.
 *
 * These helpers exist to grade B2's OUTCOME (does the tail follow? did a genuine
 * user scroll release it?) rather than the reference's bottom-distance mechanism,
 * which the rubric explicitly says is only "one valid mechanism".
 */

export type ListScrollState = {
  /** Current scroll offset of the container, in px. */
  scrollTop: number;
  /** Full scrollable content height, in px. */
  scrollHeight: number;
  /** Visible viewport height, in px. */
  clientHeight: number;
  /** Distance from the bottom edge, in px (0 == flush with the bottom). */
  bottomGap: number;
};

/**
 * Read the live-tail scroll container's geometry.
 *
 * While the list is empty (no rows mounted yet) it reports a `bottomGap` of
 * `Infinity` so `expectListAtBottom` keeps waiting instead of matching a
 * not-yet-rendered container.
 */
export async function listScrollState(page: Page): Promise<ListScrollState> {
  return page.evaluate(() => {
    let el: HTMLElement | null = document.querySelector('[data-index]');
    while (el) {
      const style = getComputedStyle(el);
      if (style.overflowY === 'auto' || style.overflowY === 'scroll') {
        return {
          scrollTop: el.scrollTop,
          scrollHeight: el.scrollHeight,
          clientHeight: el.clientHeight,
          bottomGap: el.scrollHeight - el.scrollTop - el.clientHeight,
        };
      }
      el = el.parentElement;
    }
    return { scrollTop: 0, scrollHeight: 0, clientHeight: 0, bottomGap: Number.POSITIVE_INFINITY };
  });
}

/**
 * A one-line diagnosis of a COLLAPSED live-tail list, or `null` when the geometry is
 * usable.
 *
 * The helpers discover the scroll container by walking up from a rendered row
 * (`[data-index]`), so when the live-tail list has rendered NO rows — or its scroll
 * container has no measured height — there is nothing to measure and `listScrollState`
 * reports a `bottomGap` of `Infinity` with `scrollHeight`/`clientHeight` 0. That is a
 * LAYOUT failure, not a scroll-lock behaviour, so the geometry assertions name it
 * rather than leaving a bare `Received: Infinity` for a human to decode by hand.
 */
function collapsedDiagnosis(state: ListScrollState): string | null {
  if (state.scrollHeight !== 0) return null;
  return 'the live-tail list never rendered any rows - the scroll container has no height (a layout failure, not a scroll-lock behaviour)';
}

/**
 * Attach the collapsed-layout diagnosis to a geometry assertion's failure.
 *
 * Applied ONLY to an already-thrown geometry failure, so the assertion's pass/fail
 * outcome is untouched — a container that measures normally keeps its original message,
 * and an assertion that passes never reaches here.
 */
function withCollapsedDiagnosis(error: unknown, state: ListScrollState): unknown {
  const diagnosis = collapsedDiagnosis(state);
  if (!diagnosis) return error;
  const detail = error instanceof Error ? error.message : String(error);
  const enriched = new Error(`${diagnosis}\n${detail}`);
  if (error instanceof Error && error.stack) enriched.stack = error.stack;
  return enriched;
}

/**
 * Read the tail's geometry once it has SETTLED.
 *
 * After a real wheel, `@tanstack/react-virtual` re-measures the rows that came into
 * view and corrects the container's total `scrollHeight` asynchronously (a layout
 * effect on the next frame), so a single read taken right after the wheel can catch
 * the list mid-correction and over-estimate `scrollHeight`. A baseline captured then
 * is stale: once the list settles to a smaller true height, a later single-row append
 * can never exceed it, making a "did the list grow?" comparison unsatisfiable rather
 * than merely late. This waits for two consecutive reads (a short gap apart) to agree
 * before returning the geometry, so callers capture a trustworthy baseline.
 *
 * Bounded by `timeout`: a list that never settles fails loudly instead of hanging.
 */
export async function settledListScrollState(
  page: Page,
  { timeout = 5_000, interval = 150 }: { timeout?: number; interval?: number } = {},
): Promise<ListScrollState> {
  const deadline = Date.now() + timeout;
  let previous = await listScrollState(page);
  while (Date.now() < deadline) {
    await page.waitForTimeout(interval);
    const current = await listScrollState(page);
    // `scrollHeight` must be identical; `scrollTop` is allowed a 1px sub-pixel slack
    // (the same tolerance the "viewport stayed put" assertions use).
    if (
      current.scrollHeight === previous.scrollHeight &&
      Math.abs(current.scrollTop - previous.scrollTop) <= 1
    ) {
      return current;
    }
    previous = current;
  }
  throw withCollapsedDiagnosis(
    new Error('the live-tail scroll geometry never settled'),
    await listScrollState(page),
  );
}

/** Wait until the tail is flush with the bottom of its container (auto-follow engaged). */
export async function expectListAtBottom(page: Page, message?: string): Promise<void> {
  try {
    await expect
      .poll(async () => (await listScrollState(page)).bottomGap, {
        message: message ?? 'expected the live tail to be scrolled to the bottom',
      })
      .toBeLessThanOrEqual(1);
  } catch (error) {
    throw withCollapsedDiagnosis(error, await listScrollState(page));
  }
}

/** Wait until the tail sits away from the bottom (auto-follow released). */
export async function expectListNotAtBottom(page: Page, message?: string): Promise<void> {
  try {
    await expect
      .poll(async () => (await listScrollState(page)).bottomGap, {
        message: message ?? 'expected the live tail to be scrolled away from the bottom',
      })
      .toBeGreaterThan(1);
  } catch (error) {
    throw withCollapsedDiagnosis(error, await listScrollState(page));
  }
}

/** Bounding box of the live-tail scroll container (so the mouse can be aimed at it). */
async function listBox(page: Page): Promise<{ x: number; y: number; width: number; height: number }> {
  const handle = await page.evaluateHandle(() => {
    let el: HTMLElement | null = document.querySelector('[data-index]');
    while (el) {
      const style = getComputedStyle(el);
      if (style.overflowY === 'auto' || style.overflowY === 'scroll') return el;
      el = el.parentElement;
    }
    return null;
  });
  const element = handle.asElement();
  if (!element) throw new Error('live-tail scroll container not found');
  const box = await element.boundingBox();
  if (!box) throw new Error('live-tail scroll container has no bounding box');
  return box;
}

/**
 * Scroll the live tail with a REAL mouse wheel over the list, so the app observes a
 * genuine user scroll (the real input stack) rather than a programmatic one. A
 * negative `deltaY` scrolls up, away from the bottom.
 */
export async function wheelList(page: Page, deltaY: number): Promise<void> {
  const box = await listBox(page);
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.wheel(0, deltaY);
}

/**
 * Jump the container to its bottom the way the app's own `scrollToIndex` does: set
 * `scrollTop` and fire the `scroll` event the virtualizer listens for. This is a
 * PROGRAMMATIC scroll (no user intent), so it must never release or re-engage the follow.
 */
export async function scrollListToBottomProgrammatically(page: Page): Promise<void> {
  await page.evaluate(() => {
    let el: HTMLElement | null = document.querySelector('[data-index]');
    while (el) {
      const style = getComputedStyle(el);
      if (style.overflowY === 'auto' || style.overflowY === 'scroll') {
        el.scrollTop = el.scrollHeight;
        el.dispatchEvent(new Event('scroll', { bubbles: true }));
        return;
      }
      el = el.parentElement;
    }
  });
}

/**
 * Whether the row carrying `message` is currently inside the tail's VISIBLE area.
 *
 * Playwright's own `toBeVisible()` does not account for scrolling (an element
 * scrolled out of a container still has a box), so this compares the row's box
 * against the container's viewport box (inset by its border) directly.
 */
export async function entryInListViewport(page: Page, message: string): Promise<boolean> {
  return page.evaluate((msg) => {
    let scroller: HTMLElement | null = document.querySelector('[data-index]');
    while (scroller) {
      const style = getComputedStyle(scroller);
      if (style.overflowY === 'auto' || style.overflowY === 'scroll') break;
      scroller = scroller.parentElement;
    }
    if (!scroller) return false;
    const box = scroller.getBoundingClientRect();
    const cs = getComputedStyle(scroller);
    const top = box.top + (parseFloat(cs.borderTopWidth) || 0);
    const bottom = box.bottom - (parseFloat(cs.borderBottomWidth) || 0);
    for (const row of Array.from(scroller.querySelectorAll('[data-index]'))) {
      if (!row.textContent || !row.textContent.includes(msg)) continue;
      const rowBox = row.getBoundingClientRect();
      return rowBox.bottom > top + 1 && rowBox.top < bottom - 1;
    }
    return false;
  }, message);
}

/** Assert the row carrying `message` is inside the tail's visible area. */
export async function expectEntryInListViewport(page: Page, message: string): Promise<void> {
  await expect
    .poll(() => entryInListViewport(page, message), {
      message: `expected "${message}" to be inside the visible tail area`,
    })
    .toBe(true);
}

/** Assert the row carrying `message` is NOT inside the tail's visible area (it may be unmounted). */
export async function expectEntryNotInListViewport(page: Page, message: string): Promise<void> {
  await expect
    .poll(() => entryInListViewport(page, message), {
      message: `expected "${message}" to be outside the visible tail area`,
    })
    .toBe(false);
}
