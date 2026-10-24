// Boots the Shoko-WebUI Vite dev server for the harness.
//
// Why a wrapper instead of `vite` directly:
//   * Vite must be resolved from the CHECKOUT's node_modules, not the harness's.
//   * The app's vite.config.mjs sets `server.open: "/webui/"`, which would try to
//     spawn a browser in every (headless) run — we force it off here.
//
// Env: SHOKO_WEBUI_DIR (checkout path, required), HARNESS_PORT (default 3100).
import { createRequire } from 'node:module';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const dir = process.env.SHOKO_WEBUI_DIR;
if (!dir) {
  console.error('[harness] SHOKO_WEBUI_DIR is not set.');
  process.exit(1);
}
const port = Number(process.env.HARNESS_PORT ?? 3100);

const require = createRequire(path.join(dir, 'package.json'));
let viteEntry;
try {
  viteEntry = require.resolve('vite');
} catch {
  console.error(`[harness] Could not resolve 'vite' from ${dir}. Is the checkout installed?`);
  process.exit(1);
}
const { createServer } = await import(pathToFileURL(viteEntry).href);

// The app config writes ./public/version.json and resolves ./proxy.config.js
// relative to its own dir, so run from the checkout.
process.chdir(dir);

const cfgUrl = pathToFileURL(path.join(dir, 'vite.config.mjs')).href;
const cfgMod = await import(cfgUrl).catch((err) => {
  console.error(`[harness] Failed to load ${cfgUrl}:`, err);
  process.exit(1);
});

let userConfig = cfgMod.default;
if (typeof userConfig === 'function') {
  userConfig = await userConfig({ command: 'serve', mode: 'development' });
}

const server = await createServer({
  ...userConfig,
  // We already resolved the config; don't let Vite load it a second time.
  configFile: false,
  server: {
    ...(userConfig?.server ?? {}),
    host: '127.0.0.1',
    port,
    strictPort: true,
    open: false,
  },
});

await server.listen();
console.log(`[harness] Shoko-WebUI dev server on http://127.0.0.1:${port}/webui/`);

const shutdown = async () => {
  try {
    await server.close();
  } finally {
    process.exit(0);
  }
};
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
