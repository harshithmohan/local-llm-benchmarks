You are working in the Shoko-WebUI repository — React + TypeScript + Tailwind + Vite. The logs page (`src/pages/logs/LogsPage.tsx`) currently renders only a live tail of log entries streamed over a SignalR connection; the search input on it is disabled placeholder markup.

Implement the following as one change.

## 1. Server-side log search

The page must keep showing the live SignalR tail by default, but whenever the user activates any filter — a search string or one or more level filter chips — it must switch to a server-backed search view over the full log history (not just the tail), and switch back when the filters are cleared.

- Level filter chips for Trace, Debug, Information, Warning, Error, Critical. Several can be active at once, and the filtering happens on the server, not in the client.
- The search view pages through the server's results and pulls the next page in as the user scrolls toward the end; pages join up seamlessly, oldest to newest.
- While the first fetch is in flight the view must say so; when a search comes back with nothing and nothing is loading, show an empty state that is visibly different from "still loading" and gives the user a way to clear the filters.
- The scroll-to-bottom lock belongs to the live tail only — it is off while filters are active.

## 2. Log download

- Add a download button to the logs page. With no filters it downloads the server's current log file; with filters it downloads the filtered range using the same level/search filters as the search view.
- The button shows it is working while the download is in flight, and a failure surfaces as an error toast.

## 3. Filter-expression search

The server's search accepts a filter-expression syntax on its search parameters. Users must be able to type those expressions into the search input and have them honoured — an expression the user typed is passed through as written, while ordinary text is treated as an ordinary case-insensitive substring search. Empty or blank input is not a search.

Discover the exact syntax from the server source — do not guess it.

## 4. Automatic reconnect recovery

The live tail is driven by a SignalR connection that can drop and reconnect. On reconnect the server replays a fresh backlog: reset the tail so the fresh backlog replaces the now-stale entries without losing entries that arrived around the reconnect. Do not leave stale pre-disconnect entries stranded above the fresh backlog, and keep the rest of the view consistent through the reconnect.

## 5. Cancellation and failure handling

- Cancel or ignore in-flight requests when the inputs change: a stale response must never render over newer results.
- Surface request failures: a failed read/search must produce a visible error state, distinct from the empty-results state, rather than failing silently or looking empty. The download keeps its error toast.

## Constraints

- The ShokoServer backend source is a sibling checkout next to Shoko-WebUI (`ShokoServer`). Its logging API is the source of truth: discover the endpoint paths, query parameters, response shapes and the filter-expression syntax from that source before writing any fetch calls. Sending the server something it does not accept is a failure mode you must avoid.
- Keep the existing live tail fully working: backlog delivered on connect plus new entries appended as they arrive, including across reconnects.
- Follow the project's existing conventions — how it fetches data, the shared components it already has, and how it renders long lists.
- `pnpm tscheck`, `pnpm lint` and `pnpm build` must pass when you are done.
- Leave no dead code behind.
