import type { Page, Route, WebSocketRoute } from '@playwright/test';
import {
  MOCK_BACKLOG,
  SINGLE_READ_PAGE,
  type MockEntry,
  type ReadPage,
} from '../fixtures/mock-data';

/**
 * Stubs the Shoko Server API and the SignalR logging hub, and records every
 * outbound request the app makes so specs can assert on exact parameters
 * (rubric A4/A5/A11/A12) and pagination cursors (A6).
 *
 * All API routes are matched by a glob over the `api/v3` path; the app's axios
 * client uses `baseURL: '/api/v3'`. Request routing keys off the PATH SUFFIX (e.g.
 * `Logging/Range/Read`) so the `/api/v3` prefix and API version are irrelevant.
 *
 * The bootstrap endpoints below are not what the logs feature is about, but the
 * app will not render the logs route without them (see each stub's comment).
 */

export type { ReadPage } from '../fixtures/mock-data';

export type RecordedRequest = {
  method: string;
  url: string;
  /** Path after the `/api/v3/` prefix, e.g. `Logging/Range/Read`. */
  pathname: string;
  /** First value for each query key. */
  query: Record<string, string>;
  /** Raw `URLSearchParams` membership test (detects `?level=` empty sends). */
  has: (name: string) => boolean;
  /** Parsed JSON body when present, else undefined. */
  body: unknown;
  /** Epoch ms when the request was observed. */
  at: number;
};

export type MockServer = {
  /** Every intercepted API request, oldest first. */
  requests: RecordedRequest[];
  /** Just the `Range/Read` requests. */
  readRequests: RecordedRequest[];
  /** Just the `Range/Download` + `File/Current/Download` requests. */
  downloadRequests: RecordedRequest[];
  /** Number of websocket connections to the LOGGING hub (excludes the aggregate hub). */
  wsConnections: number;
  /**
   * Number of logging-hub SignalR handshakes observed (the initial connect plus
   * every reconnect). Incremented as soon as the stub ANSWERS a logging socket's
   * handshake — i.e. BEFORE any held backlog replay is delivered — so a spec can
   * wait for a reconnect socket to be live while `holdBacklogReplay()` still holds
   * the replay (A19). Read it with `expect.poll` to avoid racing the 5 s retry.
   */
  loggingHandshakes: number;
  /** Push a live `Log` entry to every connected hub client. */
  pushLog: (entry: MockEntry) => void;
  /** Latest `Range/Read` request, if any. */
  lastRead: () => RecordedRequest | undefined;
  /**
   * Replace the backlog the stub replays on the NEXT logging handshake (initial
   * connect or a reconnect). Lets a spec serve a *fresh* backlog after a forced
   * reconnect (A19).
   */
  setBacklog: (entries: MockEntry[]) => void;
  /**
   * Close every OPEN logging-hub websocket so the app exercises its reconnect path
   * (A19). The client's automatic reconnect opens a new socket, whose handshake
   * replays the backlog set by `setBacklog`.
   */
  dropLoggingSockets: () => Promise<void>;
  /**
   * Hold the NEXT logging-hub backlog replay (A19 race window). While held, a
   * logging handshake still completes its SignalR handshake but does NOT send
   * `GetBacklog` until `releaseBacklogReplay()` resolves the gate — so a spec can
   * inject a log while the tail is mid-reconnect, then release and observe that the
   * racing entry is delivered rather than dropped. The default (never held) path
   * stays synchronous.
   */
  holdBacklogReplay: () => void;
  /** Resolve and clear a held backlog replay (no-op when not held). */
  releaseBacklogReplay: () => void;
  /** Replace the canned paging set (offset -> page). */
  setReadPages: (pages: ReadPage[]) => void;
  /** Delay `Range/Read` responses so an in-flight/searching state is observable (A8). */
  setReadDelayMs: (ms: number) => void;
  /**
   * Make `Range/Read` fail with the given HTTP status so a spec can assert the
   * read/search failure surface (A21). `null` (the default) restores the normal
   * 200 response. Like the pages and delay, the status is read when the response
   * is fulfilled.
   */
  setReadError: (status: number | null) => void;
  /** Configure the download endpoint response. */
  setDownload: (opts: { status?: number; delayMs?: number; body?: string }) => void;
};

const SIGNALR_RS = '\u001e'; // SignalR JSON protocol record separator.

/** Build a SignalR JSON-protocol invocation frame. */
const hubInvocation = (target: string, args: unknown[]): string =>
  JSON.stringify({ type: 1, target, arguments: args }) + SIGNALR_RS;

const sleep = (ms: number) => (ms > 0 ? new Promise((r) => setTimeout(r, ms)) : Promise.resolve());

const safeBody = (route: Route): unknown => {
  try {
    return route.request().postDataJSON();
  } catch {
    return undefined;
  }
};

/**
 * A serialized `WebUI_Settings` blob as the real server sends it (a JSON STRING).
 * `settingsRevision` must be > 0 or the app keeps showing its bootstrap spinner
 * (MainPage gates the whole route on it); 12 is above every entry in the app's
 * `webuiSettingsPatches` map (5..11) so no migration patch is applied.
 */
const WEBUI_SETTINGS = JSON.stringify({
  settingsRevision: 12,
  theme: 'theme-shoko-gray',
  toastPosition: 'bottom-right',
  updateChannel: 'Stable',
  serverUpdateChannel: 'Stable',
  notifications: true,
});

/** A minimal-but-valid Init/Version body (`VersionType`). TopNav reads `.Server.Version`. */
const VERSION = {
  Server: { Version: '99.0.0', ReleaseChannel: 'Stable', ReleaseDate: '2026-01-01T00:00:00Z', Commit: 'harness' },
  Commons: { Version: '1.0.0' },
  Models: { Version: '1.0.0' },
  MediaInfo: { Version: null },
  WebUI: { Version: '99.0.0', ReleaseChannel: 'Stable', ReleaseDate: '2026-01-01T00:00:00Z', Commit: 'harness' },
};

/**
 * A stable version for the update-check endpoints. TopNav runs
 * `semver.gt(updateCheck.Version, …)`, which throws on an undefined/invalid version,
 * so these must always return a parseable semver lower than the running build.
 */
const UPDATE_CHECK = { Version: '0.0.0', ReleaseChannel: 'Stable', ReleaseDate: '2026-01-01T00:00:00Z' };

export async function installMockServer(page: Page): Promise<MockServer> {
  let readPages: ReadPage[] = [...SINGLE_READ_PAGE];
  let readDelayMs = 0;
  let readErrorStatus: number | null = null;
  let downloadStatus = 200;
  let downloadDelayMs = 0;
  let downloadBody = 'harness log download body\n';
  // Backlog the stub replays on each logging handshake. Mutable so a spec can serve
  // a fresh backlog after a forced reconnect (A19). `pushLog` also appends to it, so
  // an entry that arrives while a socket is down is still in the next replay.
  let backlog: MockEntry[] = [...MOCK_BACKLOG];
  // Replay gate (A19): when set, a logging handshake awaits it before sending the
  // `GetBacklog` replay. Null by default, so the normal path never awaits.
  let replayGate: Promise<void> | null = null;
  let releaseReplay: (() => void) | null = null;

  const requests: RecordedRequest[] = [];
  const readRequests: RecordedRequest[] = [];
  const downloadRequests: RecordedRequest[] = [];
  const sockets: { url: string; route: WebSocketRoute; isLoggingHub: boolean; open: boolean }[] = [];
  // Count of logging-hub SignalR handshakes (initial connect + every reconnect),
  // incremented the instant the stub answers a logging handshake — before any held
  // replay is sent (A19).
  let loggingHandshakeCount = 0;

  const record = (route: Route): RecordedRequest => {
    const url = new URL(route.request().url());
    const query: Record<string, string> = {};
    url.searchParams.forEach((value, key) => {
      if (!(key in query)) query[key] = value;
    });
    const rec: RecordedRequest = {
      method: route.request().method(),
      url: url.href,
      pathname: url.pathname.replace(/^\/api\/v\d+\//, '').replace(/^\//, ''),
      query,
      has: (name) => url.searchParams.has(name),
      body: route.request().method() === 'GET' ? undefined : safeBody(route),
      at: Date.now(),
    };
    requests.push(rec);
    return rec;
  };

  // --- API routes -----------------------------------------------------------
  await page.route('**/api/v3/**', async (route) => {
    const rec = record(route);
    const { pathname } = rec;

    // --- Bootstrap the app queries before it will render the logs route ------
    // AuthenticatedRoute requires State === 'Started'; anything else redirects.
    if (pathname.endsWith('Init/Status')) {
      return route.fulfill({
        json: { State: 'Started', StartupMessage: '', CanShutdown: true, CanRestart: true },
      });
    }
    // Needs the nested `Server` object: TopNav reads `versionData.Server.Version`.
    if (pathname.endsWith('Init/Version')) {
      return route.fulfill({ json: VERSION });
    }
    if (pathname.endsWith('Init/DefaultUser')) {
      return route.fulfill({ json: { Username: 'admin', Password: '' } });
    }
    // MainPage keeps a spinner until `WebUI_Settings.settingsRevision > 0`.
    if (pathname === 'Settings') {
      return route.fulfill({ json: { WebUI_Settings: WEBUI_SETTINGS, FirstRun: false } });
    }
    if (pathname.endsWith('Settings/SupportedLanguages')) {
      return route.fulfill({ json: [] });
    }
    // TopNav renders the user chip from `User/Current`; transformUser throws if
    // `CommunitySites` is absent, so it is always sent (empty).
    if (pathname.endsWith('User/Current')) {
      return route.fulfill({
        json: {
          ID: 1,
          Username: 'admin',
          IsAdmin: true,
          RestrictedTags: [],
          Avatar: '',
          PlexUsernames: [],
          CommunitySites: [],
        },
      });
    }
    // TopNav runs semver.gt() on these; they must be valid, low semvers.
    if (pathname.endsWith('WebUI/LatestVersion') || pathname.endsWith('WebUI/LatestServerVersion')) {
      return route.fulfill({ json: UPDATE_CHECK });
    }
    if (pathname.endsWith('ManagedFolder')) {
      return route.fulfill({ json: [] });
    }

    // --- Core read contract --------------------------------------------------
    if (pathname.endsWith('Logging/Range/Read')) {
      readRequests.push(rec);
      await sleep(readDelayMs);
      if (readErrorStatus !== null) {
        return route.fulfill({
          status: readErrorStatus,
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ Message: 'harness read failure' }),
        });
      }
      const offset = Number(rec.query.offset ?? 0);
      const page_ = readPages.find((p) => p.offset === offset);
      return route.fulfill({
        json: page_ ? { NextOffset: page_.NextOffset, Entries: page_.Entries } : { NextOffset: null, Entries: [] },
      });
    }

    // --- Downloads -----------------------------------------------------------
    if (
      pathname.endsWith('Logging/Range/Download') ||
      pathname.endsWith('Logging/File/Current/Download')
    ) {
      downloadRequests.push(rec);
      await sleep(downloadDelayMs);
      return route.fulfill({
        status: downloadStatus,
        headers: {
          'content-type': 'text/plain',
          'content-disposition': 'attachment; filename="shoko.log"',
        },
        body: downloadBody,
      });
    }

    // Anything else the app asks for: a harmless empty object.
    return route.fulfill({ json: {} });
  });

  // --- SignalR hubs ---------------------------------------------------------
  // The app opens two hubs: `/signalr/logging` (the logs feature) and
  // `/signalr/aggregate?feeds=…` (main-page events). Both are matched by a URL
  // PREDICATE on the request path — a `**/signalr/**` glob would also match the
  // app's own source module `/src/core/signalr/signalr.ts` and serve it as
  // `text/plain`, which stops the bundle from loading.
  const isSignalrUrl = (url: URL) => url.pathname.startsWith('/signalr/');

  // A single handler for both the negotiate POST and any long-poll fallback, so
  // there is no reliance on Playwright's route precedence between two patterns.
  await page.route(isSignalrUrl, (route) => {
    const { pathname } = new URL(route.request().url());
    if (pathname.endsWith('/negotiate')) {
      // Advertise a websocket-only transport so the client opens a WS we intercept.
      return route.fulfill({
        json: {
          negotiateVersion: 1,
          connectionId: 'harness-connection',
          availableTransports: [{ transport: 'WebSockets', transferFormats: ['Text'] }],
        },
      });
    }
    // Long-polling fallback (never selected): answer 200 so nothing hangs.
    return route.fulfill({ status: 200, headers: { 'content-type': 'text/plain' }, body: '' });
  });

  await page.routeWebSocket(isSignalrUrl, (ws) => {
    const url = ws.url();
    const isLoggingHub = url.includes('/signalr/logging');
    const entry = { url, route: ws, isLoggingHub, open: true };
    sockets.push(entry);
    let handshakeDone = false;

    // SignalR keepalive. The client resets its server-timeout (default 30 s) on ANY
    // frame it receives and pings every 15 s (JSON protocol `{"type":6}`); the real
    // hub answers. With neither side pinging, the client drops the connection with
    // "Server timeout elapsed" ~30 s into a test — which both kills the live tail and
    // fires the app's reconnect path, destabilizing any spec that runs long (an A6/A11
    // assertion that has to time out already burns a full minute). Answer client pings
    // and send our own on a timer, comfortably under the client's timeout.
    const pingFrame = JSON.stringify({ type: 6 }) + SIGNALR_RS;
    const keepAlive = setInterval(() => {
      try {
        ws.send(pingFrame);
      } catch {
        // Socket already closed; nothing to do.
      }
    }, 10000);

    ws.onMessage(async (message) => {
      // The client's first frame is the JSON handshake `{"protocol":"json","version":1}\x1e`.
      if (!handshakeDone) {
        handshakeDone = true;
        ws.send('{}' + SIGNALR_RS); // handshake response
        // Mirror the hub's OnConnectedAsync: hand the live tail its backlog. This
        // runs on EVERY handshake, so a reconnect replays `backlog` again (A19).
        if (isLoggingHub) {
          // Count the handshake as answered BEFORE the (possibly held) replay, so a
          // spec can observe that a reconnect socket is live while the gate is held.
          loggingHandshakeCount++;
          // Snapshot the backlog AT HANDSHAKE TIME. A real hub reads its retained
          // history when the connection is established, so an entry logged AFTER this
          // point is delivered live on the socket and is NOT part of this replay (it
          // was never in the history the connection was handed). Snapshotting here —
          // rather than when a held gate releases — keeps the replay faithful to that
          // ordering and stops a post-handshake live push from being double-counted
          // (once live, once in the replayed history).
          const backlogSnapshot = backlog.slice();
          // A19: when a spec holds the replay, wait for the release before
          // delivering GetBacklog, so an entry pushed while the socket was DOWN
          // (before this handshake) is included. With no gate set the send stays
          // synchronous.
          if (replayGate) await replayGate;
          ws.send(hubInvocation('GetBacklog', [backlogSnapshot]));
        }
        return;
      }
      // Keepalive ping from the client: answer so its server-timeout never expires.
      if (String(message).includes('"type":6')) {
        try {
          ws.send(pingFrame);
        } catch {
          // Socket already closed; nothing to do.
        }
      }
    });

    ws.onClose(() => {
      clearInterval(keepAlive);
      entry.open = false;
    });
  });

  const server: MockServer = {
    requests,
    readRequests,
    downloadRequests,
    get wsConnections() {
      return sockets.filter((s) => s.isLoggingHub).length;
    },
    get loggingHandshakes() {
      return loggingHandshakeCount;
    },
    pushLog: (entry) => {
      // The server's own truth: append to the backlog FIRST, so an entry that
      // arrives while a socket is down is included in the next GetBacklog replay
      // (A19). The live fan-out below stays unchanged.
      backlog.push(entry);
      for (const s of sockets) {
        if (!s.isLoggingHub || !s.open) continue;
        try {
          s.route.send(hubInvocation('Log', [entry]));
        } catch {
          // Socket already closed; nothing to do.
        }
      }
    },
    setBacklog: (entries) => {
      backlog = [...entries];
    },
    dropLoggingSockets: async () => {
      const open = sockets.filter((s) => s.isLoggingHub && s.open);
      await Promise.all(open.map((s) => s.route.close()));
    },
    holdBacklogReplay: () => {
      if (!replayGate) {
        replayGate = new Promise<void>((resolve) => {
          releaseReplay = resolve;
        });
      }
    },
    releaseBacklogReplay: () => {
      releaseReplay?.();
      releaseReplay = null;
      replayGate = null;
    },
    lastRead: () => readRequests.at(-1),
    setReadPages: (pages) => {
      readPages = [...pages];
    },
    setReadDelayMs: (ms) => {
      readDelayMs = ms;
    },
    setReadError: (status) => {
      readErrorStatus = status;
    },
    setDownload: ({ status, delayMs, body }) => {
      if (status !== undefined) downloadStatus = status;
      if (delayMs !== undefined) downloadDelayMs = delayMs;
      if (body !== undefined) downloadBody = body;
    },
  };

  return server;
}

export { LOG_LEVELS } from '../fixtures/mock-data';
