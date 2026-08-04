# Phase 5 DevLog — Per-Persona Capabilities Flags (Knowledge Gate)

## Scope

The Phase 4 handoff flagged a scope fork as the first decision of this phase: whether "capabilities flags" meant (a) gating things that already exist (narrow), or (b) building out new capabilities like multimodal vision input and a web-search tool to match the `vision`/`web_search` flags (broad).

Decided **narrow**. `capabilities["knowledge"]` becomes a real gate on retrieval; `vision` and `web_search` stay exactly as they were — stored, returned, inert. Building an actual web-search tool or wiring multimodal input are different-shaped problems than a boolean gate on existing behavior, and bundling them into this phase risked the small, well-understood fix (knowledge) sitting blocked behind two open-ended research tracks. Consistent with how "build a second tool" got explicitly deferred out of Phase 3 rather than folded in.

## Components

### 1. `capabilities["knowledge"]` as a real gate in `run_chat()`

Before this phase, `has_knowledge` in `persona_service.run_chat()` was a raw DB existence check — any persona with Knowledge rows attached got retrieval attempted, regardless of what the (until now inert) `capabilities["knowledge"]` flag said.

Changed to:

```python
knowledge_enabled = (persona.capabilities or {}).get("knowledge", False)
has_knowledge = knowledge_enabled and (
    db.query(Knowledge).filter(Knowledge.persona_id == persona.id).first()
    is not None
)
```

Same pattern every capability so far has followed (Knowledge in Phase 2, Tools in Phase 3, Skills in Phase 4): a conditional inserted into the existing `run_chat()` shape, not a restructuring of it.

### 2. AND vs. replace decision

Open question from the Phase 4 handoff: does the flag replace the existence check, or gate alongside it? Decided **AND** — the flag must be true *and* rows must actually exist. The existence check stays for the same reason it existed before this phase: avoiding a wasted Ollama embedding call for a persona that has the flag on but nothing ingested yet. `and` short-circuits on `knowledge_enabled`, so the DB query is skipped entirely when the flag is off — not just the embed call.

### 3. Migration decision

Existing personas that already had Knowledge rows attached before this phase default to `capabilities.knowledge = False` (the flag was never meaningfully set before now). Decided **no migration** — no one-time data fix to flip the flag on for personas that already have documents ingested. Explicit tradeoff: any such persona goes silent on retrieval the moment this ships, until a `PUT` with `capabilities.knowledge: true` is sent. Documented here rather than fixed in code, since fixing it was explicitly declined.

### 4. Tests (`tests/test_run_chat_knowledge.py`)

Updated the existing "injects retrieved knowledge" test to explicitly set `capabilities=Capabilities(knowledge=True)` — under the old DB-existence-only logic it didn't need to, but under the new AND gate it would otherwise fail (flag defaults False).

Added two new tests to cover the AND combinations the existing pair didn't:

- `test_run_chat_skips_retrieval_when_flag_off_even_with_knowledge_rows` — flag off, rows present. This is the actual regression test for the gate: without the code change, this test fails, because the old logic would have attempted retrieval purely off row existence.
- `test_run_chat_skips_retrieval_when_flag_on_but_no_knowledge_rows` — flag on, no rows. Confirms the existence check still does its job alongside the flag, and no embed call is wasted.

Combined with the pre-existing "flag off (default), no rows" test, all four combinations of {flag on/off} × {rows present/absent} are now covered.

## Not Built Yet

Scoped strictly to what was in this phase's own (narrow) scope — the following were never in scope for Phase 5 and are deferred by explicit decision, not oversight:

- **`vision` flag** — still stored, still inert. No multimodal input wired through `ChatRequest`/`ollama_client.chat()`.
- **`web_search` flag** — still stored, still inert. No web-search tool exists in `tool_registry.py` yet; this is still the "next decision" first flagged at the end of Phase 3.
- **Data migration for pre-Phase-5 personas** — explicitly declined; see Decision #3 above.

## Live Confirmation

Ran against the real server via curl: created a persona, ingested a test document, confirmed via `/chat` with `capabilities.knowledge` off. Initial pass used "powerhouse of the cell" as the ingested detail, which turned out to be an ambiguous tell — `llama3.1:8b` already knows that phrase from training, so it wasn't clear whether the reply reflected retrieval or the model's own knowledge.

Re-ran with an artificial, training-independent detail added to the ingested text ("it is associated with the number 5") to remove the ambiguity:

- **Flag off** → reply had no mention of the number-5 association (and no way it could, since that fact only exists in the ingested chunk).
- **Flag on** → reply surfaced the number-5 detail, confirming the retrieved chunk actually reached the model via the system message.

Confirms the AND gate behaves correctly end-to-end, not just in the mocked test suite. Worth remembering for future live-confirmation passes on this project: prefer an artificial/distinctive detail over a well-known fact when testing retrieval, since a well-known fact can't distinguish "the model already knew this" from "retrieval worked."