# Prompt — variant: discovery

Paste everything below the marker into the opencode session.

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

## Constraints

- The ShokoServer backend source is available at `../ShokoServer`. Its logging API
  (REST controller + log service) is the source of truth: discover the exact endpoint
  paths, query parameters, response shapes, and the filter expression syntax the
  server accepts from that source before writing any fetch calls. Sending the server
  something it does not accept is a failure mode you must avoid.
- Keep the existing live tail fully working: backlog delivered on connect plus new
  entries appended as they arrive.
- Match existing repo conventions: TanStack Query for data fetching, the existing
  shared Input/Button/IconButton components, Tailwind utility classes like the rest
  of the app. Virtualize long lists (the repo already uses @tanstack/react-virtual).
- `pnpm tscheck`, `pnpm lint`, and `pnpm build` must pass when you are done.
- Remove any dead code your change makes obsolete (old types, old query files).
