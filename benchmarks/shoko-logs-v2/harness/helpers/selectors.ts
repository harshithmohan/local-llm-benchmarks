import { expect, type Locator, type Page } from '@playwright/test';

/**
 * DOM locators for the Shoko-WebUI logs page.
 *
 * Every locator is a semantic / user-visible hook (text, role, accessible name,
 * a public `id`, or a tooltip data attribute the app already renders) rather than
 * a component internal, so the harness asserts observable behavior and keeps
 * working across refactors of the reference implementation.
 *
 * These hooks gate SCORE A (ticket conformance), so they may only rely on things
 * `prompt.md` actually states. The ticket pins NO literal copy, so every hook below
 * is a union of several wording-agnostic strategies, each one matching structure or
 * attributes that follow from the repo's own dependencies and components (the
 * virtualizer's `data-index`, the shared Button/IconButton tooltip attribute, the
 * repo's toast library) as ONE strategy among others - never as the only strategy,
 * and never on an arbitrary copy string. Reference-cosmetic detail that the ticket never mentions
 * (the live-tail line count, the header subtitle, an input `id`) must NOT gate Score
 * A at all - it belongs to the static Score B review.
 */

/**
 * Title block proving the logs page mounted. The reference renders it as a plain
 * `<div>Logs</div>` (not a heading element), so match the exact text.
 */
export const logsHeading = (page: Page): Locator =>
  page.getByText('Logs', { exact: true }).first();

/**
 * The server-search text input.
 *
 * The ticket pins neither an `id` nor a placeholder, so resolve tolerantly, most
 * trustworthy strategy first:
 *   1. accessible name mentions "search" (what a screen-reader user perceives);
 *   2. placeholder mentions "search";
 *   3. the reference's own public `id="search"`;
 *   4. any enabled text input (the logs toolbar has exactly one).
 * The chain resolves on the reference at step 1 or 2; step 4 is the only real
 * single point of failure, and only for an implementation whose search field has
 * neither an accessible name nor a placeholder mentioning "search".
 */
export const searchInput = (page: Page): Locator =>
  page
    .getByRole('textbox', { name: /search/i })
    .or(page.locator('input[placeholder*="search" i]'))
    .or(page.locator('input#search'))
    .or(page.locator('input[type="text"]:enabled, input:not([type]):enabled'))
    .first();

/**
 * A level chip (Trace..Critical). The reference renders each chip as a button whose
 * tooltip is `${active ? 'Hide' : 'Show'} ${level} logs`; the chip itself is the
 * button's text/accessible name. Prefer the tooltip attribute, fall back to the
 * accessible name so an independent implementation still resolves.
 *
 * The name match accepts the ticket's level word OR its common short form
 * ("Info"/"Warn"/"Crit"), because these lines measure the chip's behaviour, never its
 * spelling - an exact-name requirement made a four-letter abbreviation time out
 * pagination, the parameter contract and the lock instead of measuring them, and made
 * the A4 roster assertion read a present chip as missing.
 */
const LEVEL_NAME: Record<string, RegExp> = {
  trace: /^trace\b/i,
  debug: /^debug\b/i,
  information: /^info(rmation)?\b/i,
  warning: /^warn(ing)?\b/i,
  error: /^error\b/i,
  critical: /^(critical|crit)\b/i,
};

export const levelChip = (page: Page, level: string): Locator => {
  const name = LEVEL_NAME[level.toLowerCase()] ?? new RegExp(`^${level}\\b`, 'i');
  return page
    .locator(`button[data-tooltip-content*="${level}" i]`)
    .or(page.getByRole('button', { name }))
    .first();
};

/**
 * A level chip that currently PRESENTS AS ACTIVE (A9).
 *
 * The reference does NOT put `aria-pressed` or `aria-selected` on the chip — it
 * signals the active state through its tooltip copy ("Hide Error logs" while active
 * vs "Show Error logs" while inactive) plus an active style class. So the chain tries
 * the ARIA state first (an independent implementation may well expose it) and falls
 * back to the reference's tooltip signal. `toHaveCount(0)` on this locator is the
 * tolerant "no longer active" assertion: it matches under `aria-pressed="true"`,
 * `aria-selected="true"`, the role `pressed` state, or the reference tooltip. It is
 * deliberately lenient — a candidate that signals activity some other way simply
 * resolves to 0 either way, which is why A9 also proves the reset behaviourally.
 */
export const activeLevelChip = (page: Page, level: string): Locator =>
  page
    .locator(`button[aria-pressed="true"][data-tooltip-content*="${level}" i]`)
    .or(page.locator(`button[aria-selected="true"][data-tooltip-content*="${level}" i]`))
    .or(page.getByRole('button', { name: level, exact: true, pressed: true }))
    .or(page.locator(`button[data-tooltip-content^="Hide" i][data-tooltip-content*="${level}" i]`));

/**
 * In-view "clear the filters" action shown in the empty-results state (A8/A9).
 *
 * The ticket only asks for "a way to clear the filters", so the copy is not pinned.
 * Union of the two accessible-name strategies a conformant implementation might use:
 *   1. accessible name mentions "clear" or "reset" (the reference's in-view action
 *      is a text button reading "Clear filters");
 *   2. an explicit `aria-label` mentioning "clear" or "reset".
 *
 * Deliberately NO `button[data-tooltip-content*="clear" i]` strategy here: on the
 * reference the toolbar's icon-only clear button carries exactly that tooltip, and
 * because `.or().first()` is DOM-order the always-present toolbar button would win,
 * making the A8 "an action to clear" assertion vacuously true. The toolbar button has
 * no accessible name, so the name/aria-label union resolves to the in-view action
 * (verified: 1 match, text "Clear filters", no tooltip).
 */
export const clearFiltersInView = (page: Page): Locator =>
  page
    .getByRole('button', { name: /\b(clear|reset)\b/i })
    .or(page.locator('button[aria-label*="clear" i]'))
    .or(page.locator('button[aria-label*="reset" i]'))
    .first();

/**
 * Toolbar download control.
 *
 * The ticket asks for "a way to download the logs" without pinning copy, so union
 * the strategies a conformant implementation might use:
 *   1. the shared Button/IconButton tooltip attribute (the reference's icon-only
 *      download button carries `data-tooltip-content="Download logs"`);
 *   2. an accessible name mentioning "download";
 *   3. an explicit `aria-label` mentioning "download".
 * On the reference only strategy 1 matches (the icon button has no accessible name),
 * so the union resolves to that one control and adds no false positives.
 */
export const downloadButton = (page: Page): Locator =>
  page
    .locator('button[data-tooltip-content*="download" i]')
    .or(page.getByRole('button', { name: /download/i }))
    .or(page.locator('button[aria-label*="download" i]'))
    .first();

/**
 * A VISIBLE busy affordance on the download control while a download is in flight
 * (A13).
 *
 * Derived from the RESOLVED `downloadButton(page)` locator, not re-hardcoded to the
 * reference's tooltip selector: `downloadButton` finds the control through three
 * strategies (tooltip attribute, accessible name, `aria-label`), so a candidate whose
 * control is matched by name/aria-label would otherwise have its busy affordance
 * missed (an A13 false negative). The chain is a single CSS selector list anchored to
 * the resolved control with `:scope` (which the Playwright CSS engine honours inside
 * `locator.locator()`), most semantic first:
 *   1. `aria-busy="true"` on the control itself;
 *   2. a `data-loading` marker on the control itself or a descendant;
 *   3. the reference's rendered spinner — the shared `Button` overlays an `<svg>`
 *      spinner (an mdi icon with `spin`) when `loading` is set; that svg carries a
 *      `<style>`/`@keyframes` child and an animated `<g>` inside it, so match the SVG
 *      (not the `<g>`) on either signal — a CSS list de-dupes to one element, so a
 *      reference spinner counts exactly once rather than twice;
 *   4. a `*spin*` class (e.g. Tailwind's `animate-spin`).
 * The control also disables itself, but `disabled` alone is not a *visible* indicator
 * — A13 asks for one — so this locator deliberately does not count `disabled`.
 *
 * NOTE: a single CSS list keeps `count()` deterministic; an `.or()`/`.and()` union
 * must not be used with `toHaveCount()` (documented gotcha). Assert with
 * `.first().toBeVisible()` / `.first().toBeHidden()`, or
 * `expect.poll(() => locator.count())`.
 */
export const downloadBusyIndicator = (page: Page): Locator => {
  const dl = downloadButton(page);
  return dl.locator(
    [
      ':scope[aria-busy="true"]',
      ':scope[data-loading]',
      ':scope[data-busy]',
      ':scope[data-state*="load" i]',
      ':scope[data-state*="busy" i]',
      ':scope[class*="spin" i]',
      ':scope [data-loading]',
      ':scope [class*="spin" i]',
      ':scope [class*="loading" i]',
      ':scope svg:has(style)',
      ':scope svg:has([style*="animation"])',
    ].join(', '),
  );
};

/**
 * The download control's rendered signature, for the busy signal the marker locator
 * above cannot see.
 *
 * A13 asks for a *visible* busy indicator while a download is in flight. The locator
 * can only recognise the shapes it names, and a conformant implementation may instead
 * change the control itself — swapping a download glyph for a loading glyph, dimming or
 * transforming it inline, or flipping a state attribute/class of its own — which need
 * carry none of those markers. So the spec also samples this signature before the
 * request and while it is in flight: either a recognised affordance appears, or the
 * control's own appearance changes. Both are visible to the user, and a control that
 * does nothing still fails, which is what the line is for.
 *
 * Deliberately excludes `disabled`: it is not a *visible* indicator, so a control that
 * merely disables itself must not satisfy this check. What it does sample is the
 * control's own rendering (inner HTML), its inline `style`, the state attributes that
 * mean "working" (`aria-busy` / `data-loading` / `data-busy` / `data-state`), and any
 * busy-ish class token it carries — a *change* in any of those, since a class that is
 * simply always there cannot differ between the two samples.
 */
export const downloadControlSignature = async (page: Page): Promise<string> => {
  const signature = await downloadButton(page)
    .first()
    .evaluate((el) => {
      const busyClassToken = /[^\s"'<>]*(?:spin|load|busy|progress|pending)[^\s"'<>]*/gi;
      const stateAttrs = ['aria-busy', 'data-loading', 'data-busy', 'data-state'];
      return [
        el.innerHTML,
        el.getAttribute('style') ?? '',
        ...stateAttrs.map((a) => `${a}=${el.getAttribute(a) ?? ''}`),
        (el.getAttribute('class') ?? '').match(busyClassToken)?.join(' ') ?? '',
      ].join('|');
    })
    .catch(() => '');
  return signature.replace(/\s+/g, ' ').trim();
};

/**
 * Scroll-to-bottom lock toggle.
 *
 * The ticket asks for a control that toggles "follow the tail", without pinning copy,
 * so union the strategies a conformant implementation might use:
 *   1. the shared Button/IconButton tooltip attribute (the reference's icon-only
 *      toggle carries `data-tooltip-content="Enable|Disable scroll to bottom"`);
 *   2. an accessible name describing the same behavior (scroll-to-bottom / autoscroll
 *      / follow-tail) - kept tight so it cannot match an unrelated toolbar button;
 *   3. an explicit `aria-label` mentioning "scroll";
 *   4. a `title` mentioning "scroll".
 * On the reference only strategy 1 matches; 2-4 are 0, so the union stays pinned to
 * the one toggle while widening tolerance for an independent implementation.
 */
export const scrollLockButton = (page: Page): Locator =>
  page
    .locator('button[data-tooltip-content*="scroll to bottom" i]')
    .or(page.getByRole('button', { name: /scroll\s*(to\s*(the\s*)?)?bottom|auto-?scroll|follow\s*(the\s*)?tail/i }))
    .or(page.locator('button[aria-label*="scroll" i]'))
    .or(page.locator('button[title*="scroll" i]'))
    .first();

/**
 * Rendered log rows.
 *
 * Assumption (convention-level): the ticket names no library, only "follow the project's
 * existing conventions for rendering long lists"; the repo already depends on
 * @tanstack/react-virtual, which puts `data-index` on each mounted row wrapper. An
 * implementation that swaps the virtualizer for a different library would fail this
 * hook — the ticket makes that a convention question, not a pinned requirement.
 */
export const rows = (page: Page): Locator =>
  page.locator('[data-index]');

/**
 * First-fetch in-flight status.
 *
 * The ticket only says the view must "say so" while the first fetch is in flight
 * (`prompt.md`), pinning neither wording nor DOM shape, so union:
 *   1. a generic busy/status affordance inside the logs view - `role="status"`,
 *      `aria-busy="true"`, or a spinner/loading/skeleton class. Scoped to the
 *      layout's content wrapper (which the ticket never touches) so a global nav
 *      spinner cannot satisfy the hook;
 *   2. wording-agnostic status copy: loading / searching / fetching / retrieving /
 *      looking.
 * A8 also asserts the observable in-flight behavior (no result rows while the
 * response is held), so this hook only needs to be present, not exclusive.
 */
export const searchingState = (page: Page): Locator => {
  const view = page.locator('main, .scroll-no-gutter').first();
  return view
    .locator('[role="status"], [aria-busy="true"], [class*="spinner" i], [class*="loading" i], [class*="skeleton" i]')
    .or(page.getByText(/loading|searching|fetching|retrieving|looking/i))
    .first();
};

/**
 * Empty-results state. The ticket only says an empty state "visibly different from
 * 'still loading'", so union a wording-agnostic text match with any `role="status"`
 * element carrying that same text (the latter also matches when the copy is split
 * across descendant nodes, which `getByText` on a leaf would miss).
 */
export const noResultsState = (page: Page): Locator => {
  const text = /no\b[\s\S]{0,40}\b(results?|match\w*|entr\w*|found|logs?)/i;
  return page
    .getByText(text)
    .or(page.locator('[role="status"]').filter({ hasText: text }))
    .first();
};

/**
 * Error toast surfaced by a failed request. The repo's toast library (react-toastify)
 * renders an error toast with `role="alert"` and a `Toastify__toast--error` class, so
 * union those with a class-based toast+error match; `.first()` is DOM-order and the
 * toast container element precedes its own progress-bar descendants, so it resolves to
 * the toast body (which carries the message text).
 */
export const errorToast = (page: Page): Locator =>
  page
    .locator('.Toastify__toast--error')
    .or(page.locator('[role="alert"]'))
    .or(page.locator('[class*="toast" i][class*="error" i]'))
    .first();

/**
 * A visible error affordance for a failed READ (A21).
 *
 * The ticket asks a failed read/search for "a visible error state, distinct from the
 * empty-results state", and reserves the toast for the download (A13, `errorToast`).
 * An inline failure banner is therefore a valid shape, so union:
 *   1. the toast/alert affordances above - the reference's shape;
 *   2. failure wording inside the logs view - "failed to", "could not", "unable to",
 *      "something went wrong". Deliberately NOT a bare /error/i: the "Error" level chip
 *      would satisfy that for every implementation and make this hook vacuous.
 */
export const errorAffordance = (page: Page): Locator => {
  const view = page.locator('main, .scroll-no-gutter').first();
  return errorToast(page)
    .or(view.getByText(/\b(failed to|could not|unable to|request failed|failure|something went wrong)\b/i))
    .first();
};

/**
 * Drive the search list to its end so the virtualizer reaches the trailing loader
 * row and triggers the next-page fetch.
 *
 * The scroll target is discovered structurally (the nearest scrollable ancestor of
 * a rendered row) rather than by class name, so it is independent of the tokens the
 * implementation happens to use. When the whole result set already fits the
 * container the trailing row is mounted without scrolling and the app fetches the
 * next page on its own — the poll in the spec covers both cases.
 */
export async function scrollSearchToEnd(page: Page): Promise<void> {
  await expect(rows(page).first()).toBeVisible();
  await page.evaluate(() => {
    let el: HTMLElement | null = document.querySelector('[data-index]');
    while (el) {
      const style = getComputedStyle(el);
      const scrollable = (style.overflowY === 'auto' || style.overflowY === 'scroll')
        && el.scrollHeight > el.clientHeight;
      if (scrollable) {
        el.scrollTop = el.scrollHeight;
        el.dispatchEvent(new Event('scroll', { bubbles: true }));
        return;
      }
      el = el.parentElement;
    }
  });
  // A wheel nudge helps the virtualizer emit its trailing-index effect.
  await page.mouse.wheel(0, 6000);
}
