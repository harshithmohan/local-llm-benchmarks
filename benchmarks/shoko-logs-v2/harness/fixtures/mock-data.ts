/**
 * Canned fixtures for the shoko-logs v2 harness.
 *
 * Shapes mirror the Shoko Server logging contract:
 *   Range/Read  -> { NextOffset: number | null, Entries: LogEntry[] }
 *   LogEntry    -> { TimeStamp, Level, Logger, Caller, ThreadID, ProcessID, Message, Exception? }
 *
 * Message strings are deliberately distinctive so DOM assertions cannot match a
 * different row by accident.
 */

export type MockEntry = {
  TimeStamp: string;
  Level: string;
  Logger: string;
  Caller: string;
  ThreadID: number;
  ProcessID: number;
  Message: string;
  Exception?: string;
};

const BASE_ENTRY: Omit<MockEntry, 'Message'> = {
  TimeStamp: '2026-01-02T03:04:05.000Z',
  Level: 'Information',
  Logger: 'Shoko.Server.Core.Startup',
  Caller: 'Shoko.Server.Core.Startup.Configure',
  ThreadID: 1,
  ProcessID: 4242,
};

/** Build a log entry, overriding only what a test cares about. */
export const makeEntry = (over: Partial<MockEntry> & { Message: string }): MockEntry => ({
  ...BASE_ENTRY,
  ...over,
});

/** Level names the six UI chips map to (rubric A4). */
export const LOG_LEVELS = ['Trace', 'Debug', 'Information', 'Warning', 'Error', 'Critical'] as const;

/** Entries delivered to the live tail via the SignalR `GetBacklog` invocation. */
export const MOCK_BACKLOG: MockEntry[] = [
  makeEntry({ Message: 'harness-backlog-1 server startup complete', Level: 'Information' }),
  makeEntry({ Message: 'harness-backlog-2 slow query detected', Level: 'Warning' }),
  makeEntry({ Message: 'harness-backlog-3 session cache warmed', Level: 'Debug' }),
];

/** A live entry pushed over SignalR after the page has connected (A1). */
export const LIVE_PUSH_ENTRY: MockEntry = makeEntry({
  Message: 'harness-live-push-1 arrived after connect',
  Level: 'Error',
});

/**
 * The backlog replayed on a RECONNECT handshake (A19). Distinct from MOCK_BACKLOG so
 * a spec can prove the stale pre-disconnect entries were replaced, not merely
 * appended to (and not duplicated).
 */
export const MOCK_RECONNECT_BACKLOG: MockEntry[] = [
  makeEntry({ Message: 'harness-reconnect-1 fresh backlog after reconnect', Level: 'Information' }),
  makeEntry({ Message: 'harness-reconnect-2 replayed by the server', Level: 'Warning' }),
];

/** A live entry pushed AFTER a reconnect reset, to prove appends still land (A19). */
export const POST_RECONNECT_ENTRY: MockEntry = makeEntry({
  Message: 'harness-post-reconnect-1 appended after reconnect',
  Level: 'Error',
});

/**
 * An entry pushed while the logging socket is DOWN (A19). The stub retains it in its
 * backlog, so it must be delivered by the reconnect replay — proving the down-window
 * of the reconnect race is not dropped.
 */
export const RECONNECT_DOWN_ENTRY: MockEntry = makeEntry({
  Message: 'harness-reconnect-down-1 queued while the socket was down',
  Level: 'Warning',
});

/** Page 1 of a server-search result set (returned for offset=0). */
export const SEARCH_PAGE_1: MockEntry[] = [
  makeEntry({ Message: 'harness-search-p1-a worker thread started', Level: 'Information' }),
  makeEntry({ Message: 'harness-search-p1-b downloading metadata', Level: 'Debug' }),
];

/** Page 2 of a server-search result set (returned for offset=100). */
export const SEARCH_PAGE_2: MockEntry[] = [
  makeEntry({ Message: 'harness-search-p2-a older entry', Level: 'Trace' }),
  makeEntry({ Message: 'harness-search-p2-b oldest entry', Level: 'Information' }),
];

/**
 * The default two-page result set the mock server can serve, addressed by request
 * offset: page 1 (offset 0) points at page 2 (offset 100); page 2 is terminal.
 */
export type ReadPage = {
  offset: number;
  NextOffset: number | null;
  Entries: MockEntry[];
};

export const DEFAULT_READ_PAGES: ReadPage[] = [
  { offset: 0, NextOffset: 100, Entries: SEARCH_PAGE_1 },
  { offset: 100, NextOffset: null, Entries: SEARCH_PAGE_2 },
];

/**
 * The mock server's DEFAULT result set: a single terminal page.
 *
 * A terminal first page keeps the server-search view free of incidental
 * next-page fetches, so specs that are not about pagination observe exactly the
 * read they triggered. Pagination (A6) is opted into explicitly with
 * `server.setReadPages(DEFAULT_READ_PAGES)`.
 */
export const SINGLE_READ_PAGE: ReadPage[] = [
  { offset: 0, NextOffset: null, Entries: SEARCH_PAGE_1 },
];
