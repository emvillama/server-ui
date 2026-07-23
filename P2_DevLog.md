# Persona AI Hub — Phase 2 Development Log (Knowledge / RAG)

Status as of this document: **Document ingestion pipeline complete and
tested.** Config, `embed()`, the `knowledge` table, chunking, and full
document ingestion all work end-to-end, confirmed by a 27-test suite (17
from Phase 1 + 10 new). Not yet built: similarity search, retrieval wired
into `/chat`, or any HTTP endpoint to trigger ingestion from outside a
test.

This log picks up where `P1_DevLog.md` left off. See that file for
request-flow diagrams and Phase 1 file-by-file summaries — not repeated
here.

## Context carried over from Phase 1

- Development still happens on a personal computer, not the AMD server.
  `OLLAMA_HOST` in `.env` still points at the server's LAN IP
  (`192.168.1.240:11434`). RAG needs Ollama's `/api/embeddings` endpoint,
  reached the same way `/api/chat` already is.
- Architectural conventions from Phase 1 continue to apply: routers stay
  thin, services raise plain Python exceptions (not HTTP errors),
  `ollama_client.py` is the only file allowed to call Ollama's HTTP API,
  Pydantic schemas stay separate from SQLAlchemy models, and JSON columns
  are used for flexible/evolving data.

## Project structure so far
```
server-ui/
├── .env                         # real config, gitignored
├── .env.example                 # config template, committed
├── .gitignore
├── P1_DevLog.md
├── P2_DevLog.md                 # this file
├── README.md
├── requirements.txt
├── backend/
│   ├── __init__.py
│   ├── config.py                 # UPDATED — added embedding_model
│   ├── database.py                # UPDATED — SQLite FK enforcement fix
│   ├── main.py
│   ├── models/
│   │   ├── __init__.py            # UPDATED — registers Knowledge
│   │   ├── persona.py
│   │   └── knowledge.py           # NEW — the `knowledge` table
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   └── persona.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   ├── health.py
│   │   └── personas.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ollama_client.py        # UPDATED — added embed()
│   │   ├── persona_service.py
│   │   ├── chunking.py              # NEW — chunk_text()
│   │   └── knowledge_service.py     # NEW — ingest_document()
│   └── deploy/                  # still empty — systemd unit not built yet
├── frontend/                    # still empty
├── data/                        # SQLite file lands here, gitignored
└── tests/
    ├── conftest.py
    ├── test_health.py
    ├── test_personas.py
    ├── test_chat.py
    ├── test_chunking.py          # NEW
    └── test_knowledge_service.py # NEW
```

## Milestone: embedding model confirmed pulled on server

Before writing any Phase 2 code, checked `ollama list` on the server —
`nomic-embed-text` was already pulled alongside `llama3.1:8b`. No action
needed; this was just the prerequisite check (same spirit as confirming
`OLLAMA_HOST` connectivity before Phase 1's chat endpoint).

## Milestone: `embedding_model` added to config

### `backend/config.py`
Added `embedding_model: str = "nomic-embed-text"` to the `Settings` class,
alongside the existing `default_model`. Same reasoning as every other
setting in this file: centralize the model name in one place rather than
hardcoding `"nomic-embed-text"` wherever `embed()` eventually gets called.

Decided **not** to add a dedicated test for this default (e.g. asserting
`Settings().embedding_model == "nomic-embed-text"`). Reasoning: it would
test a static assignment with no branching or logic behind it — cheap
insurance against a typo during some later unrelated edit, but not
protecting against anything likely to actually go wrong right now.
Noted as a deliberate skip, not an oversight.

## Milestone: `embed()` added to `ollama_client.py`

### `backend/services/ollama_client.py`
Added `embed(model: str, text: str) -> list[float]`, calling Ollama's
`/api/embeddings` endpoint. Mirrors `chat()`'s existing structure exactly:
same `httpx.AsyncClient` setup, same `OllamaError` wrapping for
unreachable-server / bad-status / unexpected-response-shape failures.

Takes a single string in, returns a single vector out — no batching.
Ollama's `/api/embeddings` takes one `prompt` at a time, so this matches
that; chunking logic calls this once per chunk.

## Milestone: `knowledge` table modeled

### `backend/models/knowledge.py`
The SQLAlchemy definition of the `knowledge` table — one row per chunk of
a source document, embedded and attached to a single persona.

Design decisions made explicitly before writing this (per the Phase 2
handoff notes, which called out that these shouldn't be assumed):

- **Single-persona ownership, not shared across personas.** A plain
  `persona_id` foreign key on `Knowledge`, same shape as columns on
  `Persona` itself — no join table. Reasoning: each persona in this
  project does a wildly different job (D&D GM vs. Recipe Recommender vs.
  Second Brain), so cross-persona knowledge sharing isn't a real need
  right now. Can migrate to many-to-many later if that changes — it's a
  schema change, not a rewrite.
- **Embedding stored as a JSON column**, not a separate vector table or a
  SQLite vector-search extension. Reasoning: personal scale means a plain
  Python loop over rows for cosine similarity is fast enough; adding a
  vector-search extension now would be solving a scaling problem this
  project doesn't have.
- **Chunking granularity deliberately deferred** at this point — the
  table schema doesn't care *how* a chunk was produced. (Decided in the
  next milestone below.)

Fields: `id`, `persona_id` (FK to `personas.id`, `ondelete="CASCADE"` —
deleting a persona cleans up its knowledge chunks automatically),
`source_filename` (which file a chunk came from, for later
display/debugging), `chunk_index` (0-indexed position within its source
document), `chunk_text` (the actual text that gets embedded and later
retrieved), `embedding` (JSON list of floats), `created_at`.

Also added `relationship("Persona", backref="knowledge_chunks")` — the
first use of SQLAlchemy relationships in this codebase (Phase 1 only used
raw columns). Gives `persona.knowledge_chunks` as a convenience accessor
in Python, without hand-writing a filtered query every time.

**Not done:** a separate `documents` table (one row per source file,
rather than `source_filename` repeated per chunk). Skipped for now as
more structure than needed at personal scale — revisit if re-ingesting or
replacing a single document without touching its sibling chunks becomes a
real workflow.

### `backend/models/__init__.py`
Registered `Knowledge` the same way `Persona` was registered in Phase 1:

```python
from backend.models.persona import Persona
from backend.models.knowledge import Knowledge
```

Ensures the `knowledge` table gets created by `Base.metadata.create_all()`
in `main.py`'s startup lifespan, same mechanism as Phase 1.

## Milestone: chunking strategy chosen and built

Discussed three options explicitly before implementing: fixed-size,
paragraph-based, and fixed-size-with-sentence-boundary-awareness. Chose
the third as a compromise — predictable chunk sizes like fixed-size, but
avoids cutting mid-sentence, and (unlike paragraph-based) doesn't depend
on how cleanly the source notes happen to be formatted.

### `backend/services/chunking.py`
`chunk_text(text, target_size=500, max_search=200)` — splits text into
chunks near `target_size` characters, searching up to `max_search`
characters past the target for a sentence-ending boundary (`. `, `? `,
`! `) to cut on.

**Bug caught during manual testing, not by the first round of automated
tests:** ran `chunk_text()` against a realistic paragraph (not just
uniform test sentences) and found the hard-cut fallback — used when no
sentence boundary is found nearby — could cut a word in half (e.g. "...as
it fo" / "rms the base..."). The original automated tests all passed
despite this, because they only used short, uniform sentences that never
exercised that fallback path. Fixed by changing the fallback to cut at
the nearest word boundary (last space) instead of a hard character count,
only falling back to a true hard cut if there's no space to find at all
(one giant unbroken token). Re-verified against the same paragraph after
the fix — no more mid-word cuts — and added a dedicated regression test
(`test_fallback_never_cuts_a_word_in_half`) using punctuation-free text to
lock in the fix.

### `tests/test_chunking.py`
6 tests: empty input, short input (single chunk), long input (multiple
chunks), chunks ending on sentence boundaries, the word-boundary fallback
fix, and content-preservation across reassembled chunks.

## Milestone: document ingestion built and tested end-to-end

### `backend/services/knowledge_service.py`
`ingest_document(db, persona_id, source_filename, text)` — chunks the
text via `chunk_text()`, embeds each chunk via `ollama_client.embed()`,
stores one `Knowledge` row per chunk. Reuses `get_persona()` from
`persona_service.py` so a missing persona raises the existing
`PersonaNotFoundError`, handled by the router the same way `/chat`
already does. Commits once after the full loop (not per-chunk), so a
failure partway through an embedding pass rolls back the whole ingestion
rather than leaving a half-embedded document in the database.

**Two real bugs found while testing this, both in `database.py`, not in
the ingestion logic itself:**

1. **`ondelete="CASCADE"` was silently non-functional.** SQLite doesn't
   enforce foreign keys by default, and nothing in `database.py` turned
   that on. Deleting a persona with attached knowledge threw an
   `IntegrityError` instead of cascading. Fixed by registering a
   `PRAGMA foreign_keys=ON` event listener on SQLAlchemy's `Engine`
   *class* (not a specific engine instance) — needed at the class level
   specifically because `tests/conftest.py` builds its own separate
   engine per test, independent of the app's main `engine` object, so an
   instance-level listener wouldn't have covered it.

2. **A second, subtler layer of the same bug**, at the ORM level: even
   with the DB-level pragma on, SQLAlchemy's own unit-of-work will still
   null out an already-loaded child collection itself, bypassing the
   database's `ON DELETE CASCADE` entirely. Caught because an early
   version of the cascade-delete test accessed `persona.knowledge_chunks`
   right before deleting the persona. Fixed with `passive_deletes=True`
   on the `Persona.knowledge_chunks` backref in `models/knowledge.py`.
   Confirmed via a throwaway script that `passive_deletes=True` only
   changes behavior for an *unloaded* collection — deliberately rewrote
   the final test to match how `delete_persona()` is actually called from
   the router (which never touches `knowledge_chunks` first), rather than
   testing an edge case that doesn't occur in real usage.

### `backend/database.py`
Added the `PRAGMA foreign_keys=ON` event listener described above.
Nothing else in this file changed from Phase 1.

### `tests/test_knowledge_service.py`
5 tests: ingestion creates the expected rows (with correct `chunk_index`
and per-chunk embeddings), missing persona raises `PersonaNotFoundError`,
a mid-ingestion `OllamaError` rolls back the whole batch (nothing
partially committed), the `persona.knowledge_chunks` relationship works,
and deleting a persona correctly cascades to its knowledge rows.

## Milestone: full suite green — 27 tests passing

Ran `pytest tests` against the real project — `27 passed`: the original
17 from Phase 1 plus 6 new chunking tests and 5 new knowledge-service
tests. Confirms the Phase 2 additions didn't regress anything from
Phase 1.

Two small snags hit just getting the new test file recognized at all,
worth remembering:
- `models/knowledge.py` initially raised `NameError: name 'backref' is
  not defined` when actually run — the `passive_deletes` fix required
  `from sqlalchemy.orm import relationship, backref`, but only
  `relationship` had been imported. Fixed by adding `backref` to the
  import line.
- `tests/test_knowledge_service.py` didn't show up in pytest's collected
  list at all (not an error, just silently absent) — turned out the file
  had been saved as `test_knowledge_service` with no `.py` extension, so
  pytest's `test_*.py` discovery pattern never matched it. Renamed via
  `mv tests/test_knowledge_service tests/test_knowledge_service.py`.

## Not built yet
- Similarity search (cosine similarity, plain Python loop over stored
  `embedding` columns given a query)
- Retrieval step wired into `run_chat()` in `persona_service.py` — the
  seam for this was called out explicitly in the original Phase 2 handoff
  doc
- Any HTTP endpoint (`routers/knowledge.py` + `schemas/knowledge.py`) to
  trigger ingestion from outside a test — `ingest_document()` is currently
  only callable directly in Python
- `backend/deploy/persona-ai-hub.service` (still deferred from Phase 1)
- Frontend

## Next immediate step
Build similarity search: given a query string, embed it via
`ollama_client.embed()`, compare against stored `Knowledge.embedding`
vectors for a persona (cosine similarity, plain Python loop — fine at
personal scale per the original Phase 2 handoff), return the top N
matching chunks. Once that's confirmed working on its own, wire it into
`run_chat()` as the retrieval step, then build the `/knowledge` ingestion
endpoint so documents can be uploaded without going through a test.