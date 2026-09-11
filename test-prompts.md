# Test prompts

Prompts used for benchmarking the Codacus fork. Two families: routing-trace prompts
(used to build moe-cache profiles) and server test prompts (used for prefill/decode
timing runs). All server prompts are deliberately non-repetitive - repeated text can
crash llama-server on the qwen4exp arch (see issues.md, PLE n-gram path).

## Routing-trace prompts (profile generation)

Traced with `llama-moe-trace`, ~one run each, merged per model. These are the exact
texts the existing profiles were built with - keep them unchanged so profiles stay
comparable:

- **code** - "Write a C++ function that implements an LRU cache with get() and put().
  Include the class definition, a hash map plus doubly linked list, and brief usage in
  main(). Handle capacity overflow by evicting the least recently used key."
- **chat** - "Explain the differences between TCP and UDP, when to use each, and give
  practical examples of applications that rely on them. Then briefly describe how DNS
  resolution works end to end."

## Server test prompts (prefill/decode timing)

### C# / dotnet (coding, ~300 tokens)

    Implement a thread-safe LRU cache in C# with Get and Put methods. Use a
    ConcurrentDictionary paired with a doubly linked list for O(1) recency updates, and
    protect the linked list with a lock or make operations atomic via Interlocked where
    possible. Enforce a configurable MaxCapacity: when adding beyond capacity, evict the
    least recently used entry. Then explain the tradeoffs between LRU, LFU, and FIFO
    eviction policies for a mixed read/write workload, describe how a clock
    second-chance approximation trades accuracy for simplicity in an OS page cache, and
    note when you would pick a weak-reference-based cache over a strict LRU one.

    Follow up with the same cache adapted for a distributed service: what changes when
    several nodes each hold partial state, how would you coordinate eviction across
    instances, and where does a write-through or write-back backing store fit into the
    design?

### React / TypeScript (coding, ~300 tokens)

    Build a React component that renders a searchable, virtualized data table for
    50,000 rows. It should filter as the user types (debounced to 150 ms), load more
    rows when the list scrolls near the end, and keep selection state stable across
    refetches. Use TypeScript with explicit types for the row model and the hook
    signatures.

    Then explain your choices: why virtualization is required at this scale, where you
    would move filtering to the server and what contract the API needs (cursor-based
    pagination, stable sort, total count), how you would avoid re-rendering unchanged
    rows (memoized row components, stable callbacks, keyed lists), and how the
    implementation changes if rows have variable height.

## Notes

- The payload JSON files use the models' recommended sampling: temperature 1.0,
  top_p 0.95, top_k 20, min_p 0.0; presence_penalty 1.5 for the 35B family,
  0.0 for Flash-Next. Files are per-family: `prompt-<name>-35b.json` / `prompt-<name>-flash.json`.
- Prompts are sized ~308 tokens: big enough to amortize the fixed per-request cost of
  prefill, small enough to keep decode-dominated timing runs short.
- The coding prompts above are non-repetitive by construction: no repeated sentences,
  varied technical vocabulary - safe on qwen4exp (Flash-Next) and usable as a
  stability-check prompt.
- The 35B-era timing runs used a repetitive prompt ("Explain TCP congestion control
  in detail." repeated ~110x, ~772 tokens) - valid on qwen35moe, replaced by the
  prompts above after the Flash-Next crash discovery.
- Flash-Next prefill columns were measured with a single ~240-token varied paragraph
  (database/index topic). At the target contexts (200k+), prompt size does not move
  prefill measurably; what matters is non-repetitive text and the ubatch size.
