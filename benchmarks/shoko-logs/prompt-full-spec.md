# Prompt — variant: full-spec

Same ticket as `prompt-discovery.md` plus the full behavioral spec the reference
implementation had to satisfy. Ticket body repeated in full so the file is
paste-ready.

---

You are working in the Shoko-WebUI repository — React + TypeScript + TanStack Query +
Tailwind + vite. The logs page (`src/pages/logs/LogsPage.tsx`) currently renders only
a live tail of log entries streamed over a SignalR connection; the search input on it
is disabled placeholder markup.

Implement the following two features as one change.

## 1. Server-side log search

The page must keep showing the live SignalR tail by default, but whenever the user
activates any filter — a search string or one or more level filter chips — it must
switch to a server-backed search view over the full log history (not just the tail),
and switch back when filters are cleared.

Requirements:

- Level filter chips for Trace, Debug, Information, Warning, Error, Critical. Multiple
  chips can be active at once. Level filtering happens on the server, not client-side.
- Search input debounced ~250 ms and trimmed; empty or whitespace-only input means no
  search filter.
- The search view fetches results from the server with pagination and loads more
  pages automatically as the user scrolls toward the end. Pages concatenate
  seamlessly; results are ordered oldest to newest (ascending).
- While the first fetch is in flight, show a "searching the full log history" state;
  when results come back empty and nothing is loading, show a "no results" state with
  a "Clear filters" action.
- The scroll-to-bottom lock applies only to the live tail; it is disabled while
  filters are active.

## 2. Log download

- Add a download button to the logs page. When no filters are active it downloads the
  server's current log file; when filters are active it downloads the filtered range
  using the same level/search filters as the search view.
- Show a loading state on the button while the download is in flight, and an error
  toast on failure.

## API reference (from ShokoServer)

Endpoints (relative to the API base the app's axios instance already uses):

- `GET Logging/Range/Read?offset=<n>&limit=<n>&descending=<bool>&level=<names>&message=<expr>`
  — reads log entries over the full history. `offset` is the page start, `limit` the
  page size, `descending=false` gives ascending order. `level` is a comma-separated
  list of level names (e.g. `Warning,Error`); omit it for no level filter.
  `message` is an optional filter expression (DSL below); omit it for no message
  filter. Inactive filters must be omitted entirely, not sent empty.
  Response: `{ NextOffset: number | null, Entries: LogEvent[] }` — `NextOffset` is
  the offset of the next page, or null when there are no more entries.
- `GET Logging/File/Current/Download` — downloads the current log file as plain text.
- `GET Logging/Range/Download?level=<names>&message=<expr>` — downloads the filtered
  range as plain text, same filter semantics as Range/Read.

`LogEvent` fields: `TimeStamp` (string), `Level` (one of
`Trace | Debug | Information | Warning | Error | Critical | None`, serialized as a
string), `ThreadID?`, `ProcessID?`, `Logger?`, `Caller?`, `Message`, `Exception?`.
The optional fields may be absent from the payload — handle their absence.

## Full behavioral spec

These edge cases are part of the acceptance criteria:

1. **Filter expression wrapping.** A bare search payload is shorthand for
   *case-sensitive* contains, so plain user text must be wrapped to make it
   case-insensitive. But the mode prefix is not just a prefix: the grammar is a mode
   character first (`c`, `=`, `^`, `$`, `~`, `*`), optionally followed by at most one
   `!` (negate) and one `#` (case-insensitive) modifier in *either order*, then `:`.
   `!` and `#` are modifiers, never prefixes on their own — `!c:foo` and `#:foo` are
   server-side 400s. So: text that already matches the full grammar must pass through
   untouched; anything else (including text that merely *starts with* a mode char, or
   starts with `!`/`#`) must be wrapped as a literal case-insensitive contains. An
   empty search must not be wrapped or sent at all.
2. **Query-key stability.** If the active level set is a `Set`, it must not be put in
   the query key as-is (a `Set` serializes to `{}` in the key hash): derive a stable,
   content-sensitive key from it, sorted so chip-toggle order never changes the key.
   Level toggles must trigger a refetch with the new filter, and must not be lost.
3. **Param hygiene.** Empty `message`/`level` filters are omitted from the request
   entirely — never sent as empty strings or empty DSL operands.
4. **Pagination.** Next-page fetches are triggered from an effect keyed on the
   trailing virtual row (a render-phase side effect is not acceptable); `hasNextPage`
   must be false before the first load completes (not an off-by-one that shows a
   phantom loader row), and exhausted when `NextOffset` is null.
5. **Loading states.** The full-height "searching" spinner is gated to the initial
   fetch only — subsequent page fetches must not blank the view; a phantom loader row
   appears at the end while the next page loads.
6. **Scroll lock.** While the live tail is locked to the bottom, the only thing that
   may unlock it is the user scrolling up; detect it with a bottom check
   (`scrollHeight - scrollTop - clientHeight > 1` while locked), not by comparing
   scrollTop snapshots over time — virtualizer measurement corrections and the
   programmatic scroll-to-bottom itself would otherwise look like a user scroll-up
   and disable the lock as soon as logs load. The virtualizer also needs a
   scroll-rect workaround (patching `rowVirtualizer.scrollRect` from the container's
   live dimensions) or measurement breaks in Firefox and Chrome.
7. **Live tail integrity.** The server re-sends the backlog on every SignalR
   reconnect; on reconnection the tail must be reset so the fresh backlog replaces
   stale entries instead of duplicating them. Timestamps are formatted for display in
   the row component, not pre-formatted in the data layer.
8. **Download.** The axios instance unwraps `response.data` in an interceptor, so the
   server's `Content-Disposition` filename is unreachable — derive the filename
   locally (timestamped `shoko-logs-<datetime>.txt`). The blob URL must be revoked
   on a deferred timer (an immediate revoke can cancel the download in
   Firefox/Safari), and the anchor must be attached to the DOM for the `download`
   attribute to work in Firefox. The download mutation receives the user's debounced
   search text and level set and derives the endpoint the same way the page decides
   between live and search view.

## Constraints

- Keep the existing live tail fully working: backlog delivered on connect plus new
  entries appended as they arrive.
- Match existing repo conventions: TanStack Query for data fetching, the existing
  shared Input/Button/IconButton components, Tailwind utility classes like the rest
  of the app. Virtualize long lists (the repo already uses @tanstack/react-virtual).
- `pnpm tscheck`, `pnpm lint`, and `pnpm build` must pass when you are done.
- Remove any dead code your change makes obsolete (old types, old query files).
