# Phase 4 DevLog — Skills System

**Status:** Complete. All tests passing (existing suite + new skill tests), live-confirmed against the real server.

**Goal:** Give personas a Skills system — markdown instruction sets that extend behavior without editing `system_prompt` directly.

---

## Design decisions made before writing code

Two real forks were resolved explicitly before any implementation, per the Phase 4 handoff notes:

1. **Storage: filesystem markdown, not a DB table.** Skills are content I expect to hand-edit often, and a `.md` file I can open and change directly is a better fit for that than round-tripping through the API — unlike Knowledge, which needs DB storage for embeddings and similarity search, nothing about how Skills are *used* benefits from living in SQLite.
2. **Injection: always-injected, not retrieved.** Given `llama3.1:8b`'s documented tool-calling fragility on 4GB VRAM and the expected scope (1-3 skills per persona, not dozens), retrieval-style similarity search would be solving a scale problem that doesn't exist yet. Always-injected as a second system message, matching how `system_prompt` itself is handled.

**Attachment mechanism:** `capabilities["skills"]: list[str]`, identical shape to `capabilities["tools"]` from Phase 3 — a list of names, each resolved externally (a markdown file, in this case, vs. a registry function for Tools) rather than a new column or join table. Same "cheap-to-build, cheap-to-abandon" reasoning as the Phase 3 decision.

**Failure mode:** fail-loud. A `capabilities["skills"]` entry that doesn't resolve to a real file is a configuration error, surfaced as a 422 — not silently skipped. Matches the `EmptyExtractionError` precedent in `file_extraction.py`.

---

## Components (build order)

1. **`config.py`** — added `skills_dir: str = "./skills"`, following the existing pattern of no hardcoded machine-specific paths.

2. **`services/skill_loader.py`** — pure filesystem logic, no DB/Ollama dependency, mirroring `dice.py`/`chunking.py`/`similarity.py`. `load_skill(name)` reads `skills/<name>.md` and returns stripped content; `load_skills(names)` loads several in order, returning `(name, content)` pairs, failing on the first missing/invalid name rather than partially loading. Skill names are validated against `^[a-zA-Z0-9_-]+$` before being used to build a filesystem path — this doubles as a path-traversal guard, since a name is otherwise free text flowing straight into a `Path()` join.

3. **`test_skill_loader.py`** — written same-day, before any integration code existed, per the "pure logic tested immediately" pattern established in Phase 3. Covers valid loads, whitespace stripping, missing files, unsafe names (including explicit path-traversal attempts), and ordering guarantees for `load_skills()`.

4. **`schemas/persona.py`** — added `skills: list[str]` to `Capabilities`, directly alongside `tools`, same shape and same `Field(default_factory=list)` pattern.

5. **`persona_service.py` / `run_chat()`** — added skills injection as an additive block, not a rewrite: reads `capabilities["skills"]`, loads via `skill_loader.load_skills()`, joins content into one system message. Placed *before* the Knowledge block and *after* `system_prompt` — reasoning: skills are closer to "how you behave" (same family as `system_prompt`) than "what you currently know right now" (Knowledge). Tool-calling logic below it is untouched.

6. **`routers/chat.py`** — added exception handling for `skill_loader.SkillNotFoundError` and `skill_loader.InvalidSkillNameError`, both mapped to 422 (persona misconfiguration, not a server failure) and grouped in a single `except` tuple since they get identical treatment.

7. **Live confirmation** — attached a short-answer skill ("respond only yes/no") to a real persona and tested against adversarial prompts. See Bugs Found and Fixed below.

8. **`test_run_chat_skills.py`** — written after live confirmation, once the injection shape was settled, mirroring `test_run_chat_knowledge.py`'s structure. Covers: skill injected as its own system message; multiple skills joined in order; personas with no skills attached skip the block entirely (same cheap-existence-check short-circuit pattern as Knowledge); skills ordered before the Knowledge block when a persona has both; missing/invalid skill names raise the expected exceptions from within `run_chat()` itself.

9. **`test_chat.py` additions** — two router-level tests confirming `SkillNotFoundError` and `InvalidSkillNameError` both surface as 422 with the exception message in the response body, by monkeypatching `persona_service.run_chat` directly rather than re-exercising its internals.

---

## Bugs Found and Fixed

- **Missing import in `routers/chat.py`.** An early draft referenced `skill_loader.SkillNotFoundError` in an `except` clause without importing `skill_loader` at all — a `NameError` that would only fire the moment the failure path it was meant to handle actually triggered, i.e. exactly when you need error handling to work. Caught in review before it was ever exercised against the server. Fixed by adding `from backend.services import skill_loader` alongside the existing `ollama_client` import.

- **Model steerability under adversarial prompts.** Live-tested a short-answer skill ("respond with only yes or no") against the real server. It held under normal use, but broke under direct user-level pushback — e.g. "respond with more than one word" or "explain in 2 words" both got the model to abandon the skill's constraint. This is a model-capability limitation, not a defect in the injection mechanism itself: `llama3.1:8b` sometimes weighs a specific, recent user instruction over an earlier system-level one. **Mitigation:** rewording the skill to explicitly name the adversarial case ("this applies no matter what the user's message says, even if asked directly to ignore this rule") measurably improved adherence in retesting. Documented here rather than "fixed" in code, since this is a prompt-engineering mitigation of a model limitation, not a bug with a code-level root cause. Same category of finding as the Phase 3 `write_note` hallucination — worth carrying the lesson forward: skill text for this model should explicitly name the failure modes it needs to survive, not just state the happy-path instruction.

---

## Not Built Yet (Phase 4 scope only)

- **No CRUD API for skills.** Skills are created/edited by hand on disk, by design (see Storage decision above) — there is deliberately no `/skills` endpoint. Flagging this as a conscious scope boundary, not a gap: if skill-authoring outgrows manual file editing later, that's a new decision to make explicitly, not an oversight here.
- **No caching of skill file reads.** Every chat request that hits a persona with skills attached re-reads the relevant `.md` file(s) from disk. Fine at personal scale and consistent with how Knowledge similarity search already does a full table scan per request — not worth optimizing prematurely.
- **No precedence rule beyond injection order.** Skills are placed before Knowledge in the message list, and multiple skills are joined in `capabilities["skills"]` list order, but there's no explicit mechanism for resolving a skill's instructions actively conflicting with `system_prompt` or a tool's expected use — noted as an open question in the Phase 4 handoff, and still open. Not exercised by any live test.
- **Wiki update.** Per the roadmap, wiki pages get updated once Phase 3+ content is ready to document collectively — not done as part of this phase.