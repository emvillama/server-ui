# Phase 3 DevLog — Tools

**Status:** Complete. Dice roller tool built, wired into chat, and confirmed working live against the real server (192.168.1.240) across multiple test messages.

## Project structure (additions this phase)
```
server-ui/
├── P3_DevLog.md # this file
├── backend/
│ ├── schemas/
│ │ └── persona.py # Capabilities.tools: bool -> list[str]
│ ├── services/
│ │ ├── dice.py # pure dice notation parser/roller
│ │ ├── tool_registry.py # tool name -> {schema, execute} mapping
│ │ ├── ollama_client.py # added chat_with_tools()
│ │ └── persona_service.py # run_chat() wired for tool-calling
└── tests/
├── test_dice.py
├── test_tool_registry.py
└── test_run_chat_tools.py
```
## Context carried over from Phase 2

- Routers stay thin; all logic lives in `services/`.
- Services raise plain Python exceptions; routers translate to HTTP status codes.
- `ollama_client.py` remains the only file that calls Ollama's HTTP API.
- Pure-logic functions live in their own file, tested in isolation, separate from anything touching the DB or Ollama (`chunking.py`, `similarity.py` precedent — `dice.py` follows the same pattern).
- Shared test fixtures (`client`, `persona`, `db`) live in `conftest.py`, reused rather than redefined.
- `capabilities` JSON column exists but wasn't functionally meaningful until this phase gave `tools` a real, if narrow, purpose.

## Components (in the order they were built)

1. **`services/dice.py`** — Pure dice-notation parser and roller (`parse_notation()`, `roll_dice()`). No I/O, no Ollama/DB awareness, same isolation pattern as `chunking.py`/`similarity.py`. Sanity caps (`MAX_DICE=100`, `MAX_SIDES=1000`) added as cheap insurance against a hallucinated tool call requesting something absurd.

2. **`tests/test_dice.py`** — Written immediately after `dice.py`, not deferred to end of phase, since its interface was stable and isolated from every downstream design decision. This turned out to be the right call: every integration-level design (tool schema, attachment mechanism, round-trip flow) changed at least once during the phase, but `dice.py` never did.

3. **`Capabilities.tools` schema change** — Changed from `bool` to `list[str]` in `schemas/persona.py`, so a persona can be attached to zero or more tools by name (e.g. `["dice_roller"]`). Decided explicitly over two alternatives (a dedicated `persona_tools` join table, or hardcoding persona↔tool pairs) after weighing the low switching cost of starting with a JSON list against the greater cost of building relational infrastructure for what's currently a single tool. No existing personas needed migration — only test personas existed at the time.

4. **`services/tool_registry.py`** — Maps a tool name to its Ollama-facing JSON schema and its executor function. A plain Python dict, deliberately not a database table — there's no tool metadata that needs to persist or be queried beyond what's already expressed in code. `get_tool_schemas()` silently skips unknown/stale tool names rather than raising; `get_tool_executor()` returns `None` for unregistered tools rather than crashing.

5. **`ollama_client.chat_with_tools()`** — Added as a new function alongside the existing `chat()`, which was left completely untouched (same signature, same return type, same callers). Returns the full assistant message dict from Ollama (not just content text), since completing a tool-call round trip requires re-appending that exact message — including its `tool_calls` field — into the conversation history.

6. **`persona_service.run_chat()` wiring** — Checks `persona.capabilities["tools"]`; if non-empty, calls `chat_with_tools()` instead of `chat()`. If the model returns `tool_calls`, executes each via the registry, appends the results as `"tool"` role messages, and makes a single follow-up `chat()` call for the final natural-language reply. Deliberately not recursive/looped — one round trip only, given `llama3.1:8b`'s documented tool-calling fragility from the Open WebUI history. Personas with no tools attached go through the exact same `chat()` path as before this phase — confirmed via test that `chat_with_tools()` is never even called for them.

7. **Live confirmation against the real server** — Sent real chat messages to the D&D GM persona over LAN. Confirmed via temporary debug prints that Ollama returns `tool_calls` with `arguments` as an already-parsed dict (not a JSON string, which had been an open risk), that `dice_roller` executes correctly, and — critically — that the number in the model's final narration matched the tool's actual computed total across three separate live test runs. Debug prints removed after confirmation.

8. **`tests/test_tool_registry.py` and `tests/test_run_chat_tools.py`** — Written after live confirmation, not before, since the round-trip flow's shape was genuinely uncertain until then (unlike `dice.py`, which was stable from the start). Covers: schema lookup and execution (including bad-argument and unknown-tool cases) in isolation, plus `run_chat()` integration cases — tool executed and result correctly reflected in the final reply, tools skipped entirely for personas with none attached, no wasted follow-up call when the model declines to use an offered tool, and graceful handling of a hallucinated/unregistered tool name. All 110 tests pass (96 pre-existing + 14 new).

## Bugs found and fixed

- **Test assertion error in `test_run_chat_executes_tool_and_returns_final_reply`**: initially asserted the user message was `messages[-1]`, copied from the Phase 2 knowledge-retrieval test's pattern. That assumption doesn't hold once a tool round-trip appends the assistant's tool-call message and the tool result *after* the user message — fixed by asserting the correct relative ordering instead (user message, then tool-call message, then tool result).

## Known gaps discovered (not fixed this phase — flagged for awareness)

- **Zeroed-out `params` from Swagger's auto-filled example values are not filtered as "unset."** `OllamaParams` fields like `num_ctx: 0` or `repeat_penalty: 0` pass `ollama_client.chat()`'s `v is not None` filter and get sent to Ollama as real (degenerate) generation parameters — `num_ctx: 0` in particular produced garbled/repeated-token output during testing. This isn't a Phase 3 code bug (the filtering behavior is unchanged from Phase 1), and it surfaced by coincidence during live tool testing rather than because of anything tools-specific. Worth a future decision: validate/reject clearly-unintended zero values, or leave it as a documented Swagger-usage gotcha.

## Not built yet (within this phase's own stated scope)

- **No persisted unit test for `ollama_client.chat_with_tools()` in isolation** — it was verified via an ad hoc mocked-`httpx` script during development and is exercised indirectly through the `run_chat()` integration tests (which monkeypatch it directly), but there's no `test_ollama_client.py` covering its own request/response/error-handling behavior the way `chat()` and `embed()` implicitly are via other tests.
- **A second tool** — deliberately out of scope per the phase's "narrow, confirm reliability first" philosophy. The dice roller is confirmed reliable; a second tool is the natural next candidate but wasn't started this phase.
- **No retry/self-correction loop beyond a single follow-up call** — if the model requests a second tool call in its follow-up response, that request is simply returned as inert text rather than acted on. Acceptable for the current single-tool scope; would need revisiting if a tool ever benefits from multi-step use.

## Next immediate step

Decide whether to build a second tool now (web search was the concrete candidate raised during the attachment-mechanism discussion) or move on to Phase 4 (Skills) with the dice roller as Phase 3's sole, confirmed deliverable — consistent with the phase's own "one tool, prove it works, then decide" mandate.