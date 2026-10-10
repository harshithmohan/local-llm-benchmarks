<!--
Model-card template. Copy to models/<rig>/<model>.md and fill the placeholders.
Keep the section order; if a section has no data, keep its heading and mark it
("not yet run" / "see the archive") rather than deleting it.

Audience: someone who wants to pick a config and replicate it in one glance.
Rule of thumb - a fact belongs here only if it is specific to THIS model/config.
Global protocol -> methodology.md §Measurement methods. Prompt history, retired
engines, failed quants -> archive/<model>.md. Prompt texts -> test-prompts.md.

Public file: no host / ssh / docker / absolute-path ops info. Use <models>/ style
placeholders. Name engines explicitly ("moe-cache fork", "stock"), never "both".
-->

# <Model> (Rig N) - recommended configs

Updated: <YYYY-MM-DD> · [full experiment log](archive/<model>.md) · [methodology](../../methodology.md)

`<quant(s)>` (`<arch>`, native ctx <n>, <embedded MTP head | no MTP>). Model cards:
[<org>/<repo>](https://huggingface.co/<org>/<repo>) (`<quant>`).

## Recommended configs

<!-- One row per recommended, usable config - the headline answer. "Config" is the
     quant/quant+ctx; fold cache size and -b/-ub into Notes (they are not universal).
     Anything not recommended lives on the model page or in the archive. -->

| Config | ctx | engine | MTP | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| <quant> | <ctx> | <engine> | <on or off> | <prefill> | **<decode>** | <VRAM> MiB | <cache N, `-b/-ub N`> |

## Configs

<!-- One subsection per row above. Give only the replication-critical caveats
     (a flag that must match, a YaRN rule). No rationale essays -
     that is the archive's job. -->

### <quant> <ctx label> - <engine>, <one-line summary>

    llama-server --port PORT \
      -m <models>/<file>.gguf \
      --ctx-size <ctx> -ngl all -fit off \
      <cache / engine flags> \
      --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on \
      --load-mode none --no-mmproj-offload --threads <n> --parallel 1 \
      <MTP flags; omit the line when MTP is off> \
      -b <b> -ub <ub> \
      --temp <t> --top-k <k> --min-p <m>

## Notes

<!-- Only model-specific caveats a replicator must know (a flag that must match, an
     issues.md link, a non-obvious limit that would break or surprise a replication).
     Do not explain why a value was chosen or how it compares to alternatives - that is
     tuning/comparison data, and belongs in the archive. Drop global/protocol facts -
     they live in methodology.md. -->

- <quirk or caveat>

## Long-context refactor benchmark

<!-- Keep this heading even before the runs exist (mark "not yet run"). Same table
     shape as Recommended configs; the ~60K and ~120K tasks are described in
     test-prompts.md and run under the same protocol as the rows above. Every window
     is checked on the ~60K prompt; a window above 140k is additionally checked on the
     ~120K prompt - the one that exercises that window's prompt-side buffers. One row
     per prompt size run. -->

<one-line task description + link to test-prompts.md; state "same protocol as the
recommended configs" rather than restating flags.>

| Config | ctx | engine | MTP | prompt | prefill t/s | decode t/s | VRAM | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <quant> | <ctx> | <engine> | <on or off> | ~60K | <prefill> | **<decode>** | <VRAM> MiB | <cache N> |
| <quant> | <ctx> | <engine> | <on or off> | ~120K | <prefill> | **<decode>** | <VRAM> MiB | <cache N> |
