import { test as base } from '@playwright/test';
import { seedAuth } from './app';
import { installMockServer, type MockServer } from './mock-server';

/**
 * The harness `test` fixture: for each test it seeds an authenticated session
 * and installs the API + SignalR stub, exposing the mock server (with its
 * recorded requests) to the test body.
 *
 *   import { test, expect } from '../helpers/fixtures';
 *   test('...', async ({ page, server }) => { ... });
 */
export const test = base.extend<{ server: MockServer }>({
  server: [
    async ({ page }, use) => {
      await seedAuth(page);
      const server = await installMockServer(page);
      await use(server);
    },
    // Automatic: every test gets the seeded session + stub, even if it never
    // names `server` in its fixture list.
    { auto: true },
  ],
});

export { expect } from '@playwright/test';
