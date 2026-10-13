import { test, expect } from '../helpers/fixtures';
import { openLogsPage } from '../helpers/app';
import { searchInput } from '../helpers/selectors';

/**
 * A17 / A18 — DSL-aware search (runtime).
 *
 * A17 (17): a search expression that matches the server's filter-expression prefix
 *           grammar is recognised and sent UNCHANGED (no `c#:` wrapping).
 * A18 (8):  only plain, non-DSL input is wrapped as a case-insensitive contains
 *           (`c#:`); an empty search is neither wrapped nor sent.
 *
 * Grammar (rubric "Server contract" + ShokoServer `LogService.TryParseLogFilterDsl`):
 *   mode char [c=^$~*] , at most one `!` and at most one `#` (either order) , `:` , payload
 * The trailing `:` is REQUIRED for an input to be DSL at all: with no colon the server
 * treats the whole string as a case-SENSITIVE literal contains, so the reference
 * client's `hasDslPrefix` regex also requires the colon. The ticket's illustrative
 * `^GET /api` has no colon and is therefore NOT grammar-valid (it is wrapped as
 * `c#:^GET /api`); the grammar-faithful starts-with expression is `^:GET /api`, which
 * is what is asserted here. Reported to the rubric owner rather than encoded as a
 * failing assertion (which would penalise a correct implementation).
 */

test.describe('A17 — DSL expressions are sent through verbatim', () => {
  test('a starts-with expression (`^:…`) is sent unchanged', async ({ page, server }) => {
    await openLogsPage(page);
    const before = server.readRequests.length;
    await searchInput(page).fill('^:GET /api');
    await expect.poll(() => server.readRequests.length).toBeGreaterThan(before);
    expect(server.lastRead()!.query.message).toBe('^:GET /api');
  });

  test('a regex expression (`*:…`) is sent unchanged', async ({ page, server }) => {
    await openLogsPage(page);
    const before = server.readRequests.length;
    await searchInput(page).fill('*:timeout.*');
    await expect.poll(() => server.readRequests.length).toBeGreaterThan(before);
    expect(server.lastRead()!.query.message).toBe('*:timeout.*');
  });

  test('a mode + ignore-case flag expression (`c#:…`) is sent unchanged', async ({ page, server }) => {
    await openLogsPage(page);
    const before = server.readRequests.length;
    await searchInput(page).fill('c#:WARN');
    await expect.poll(() => server.readRequests.length).toBeGreaterThan(before);
    expect(server.lastRead()!.query.message).toBe('c#:WARN');
  });
});

test.describe('A18 — plain terms are wrapped, empty input is not sent', () => {
  test('a plain term is wrapped as a case-insensitive contains', async ({ page, server }) => {
    await openLogsPage(page);
    const before = server.readRequests.length;
    await searchInput(page).fill('server');
    await expect.poll(() => server.readRequests.length).toBeGreaterThan(before);
    expect(server.lastRead()!.query.message).toBe('c#:server');
  });

  test('a whitespace-only search is neither wrapped nor sent', async ({ page, server }) => {
    await openLogsPage(page);
    const before = server.readRequests.length;
    await searchInput(page).fill('   ');
    // Past the ~250 ms debounce, with margin.
    await page.waitForTimeout(700);
    expect(server.readRequests.length).toBe(before);
  });
});

/**
 * A17 / A18 boundary cases — colon-bearing literals are ordinary text.
 *
 * The DSL is only engaged when the colon is preceded by a valid mode char followed by
 * at most one `!` and one `#` in either order (ShokoServer
 * `LogService.TryParseLogFilterDsl`, `LogService.cs:824-908`): the char before the
 * colon must be in `[c=^$~*]` AND every char between it and the colon must be `!` or
 * `#` (any other char fails with "Invalid character … in modifiers"). A detector that
 * merely tests "first char in the mode set AND a colon exists" accepts malformed heads
 * such as `cfoo:bar` and forwards them to the server, which then rejects the whole
 * search — so these cases pin that a colon-bearing literal is sent WRAPPED as ordinary
 * text (`c#:`), never passed through as an expression. `http://x` and `a:b` also guard
 * a detector that keys on colon presence alone (`h`/`a` are not mode chars).
 */
test.describe('A17/A18 boundary — colon-bearing literals are wrapped, not honoured', () => {
  test('a literal URL containing a colon is wrapped as ordinary text', async ({ page, server }) => {
    await openLogsPage(page);
    const before = server.readRequests.length;
    await searchInput(page).fill('http://x');
    await expect.poll(() => server.readRequests.length).toBeGreaterThan(before);
    expect(server.lastRead()!.query.message).toBe('c#:http://x');
  });

  test('a bare `a:b` literal is wrapped as ordinary text', async ({ page, server }) => {
    await openLogsPage(page);
    const before = server.readRequests.length;
    await searchInput(page).fill('a:b');
    await expect.poll(() => server.readRequests.length).toBeGreaterThan(before);
    expect(server.lastRead()!.query.message).toBe('c#:a:b');
  });

  test('a malformed expression head (`cfoo:bar`) is treated as ordinary text', async ({ page, server }) => {
    await openLogsPage(page);
    const before = server.readRequests.length;
    await searchInput(page).fill('cfoo:bar');
    await expect.poll(() => server.readRequests.length).toBeGreaterThan(before);
    expect(server.lastRead()!.query.message).toBe('c#:cfoo:bar');
  });
});
