# Persona AI Hub — Phase 2 Development Log (Knowledge / RAG)

Status as of this document: **Phase 2 (Knowledge/RAG) just started.**
Config updated, `embed()` added to the Ollama client, and the `knowledge`
table modeled and registered. Not yet built: document ingestion/chunking,
similarity search, or wiring retrieval into `/chat`.

This log picks up where `P1_DevLog.md` left off. See that file for
project structure, request-flow diagrams, and Phase 1 file-by-file
summaries — not repeated here.

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
server-ui/
├── .env                         # real config, gitignored
├── .env.example                 # config template, committed
├── .gitignore
├── P1_DevLog.md
├── P2_DevLog.md                 # NEW — this file
├── README.md
├── requirements.txt
├── backend/
│   ├── __init__.py
│   ├── config.py                 # UPDATED — added embedding_model
│   ├── database.py
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
│   │   └── persona_service.py
│   └── deploy/                  # still empty — systemd unit not built yet
├── frontend/                    # still empty
├── data/                        # SQLite file lands here, gitignored
└── tests/
    ├── conftest.py
    ├── test_health.py
    ├── test_personas.py
    └── test_chat.py

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
that; chunking logic (Phase 2, later) will call this once per chunk.

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
- **Chunking granularity deliberately deferred.** The table schema doesn't
  care *how* a chunk was produced — it just needs a column for chunk text
  and a chunk index. The fixed-size vs. paragraph-based decision gets made
  when document ingestion is actually built (next milestone), likely by
  testing against real notes rather than deciding in the abstract.

Fields: `id`, `persona_id` (FK to `personas.id`, `ondelete="CASCADE"` —
deleting a persona cleans up its knowledge chunks automatically),
`source_filename` (which file a chunk came from, for later
display/debugging), `chunk_index` (0-indexed position within its source
document), `chunk_text` (the actual text that gets embedded and later
retrieved), `embedding` (JSON list of floats), `created_at`.

Also added `relationship("Persona", backref="knowledge_chunks")` — the
first use of SQLAlchemy relationships in this codebase (Phase 1 only used
raw columns). Gives `persona.knowledge_chunks` as a convenience accessor
in Python, without hand-writing a filtered query every time. Flagged
explicitly since it's a new pattern, not just a new file.

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

## Not built yet
- Document ingestion + chunking (chunking strategy still undecided)
- Similarity search (cosine similarity, plain Python loop over rows)
- Retrieval step wired into `run_chat()` in `persona_service.py`
- Any endpoint for uploading/attaching knowledge to a persona
- Tests for any of the above

## Next immediate step
Decide chunking strategy (fixed-size vs. paragraph-based) against real
source material — likely the actual university notes intended for the
Second Brain/Study Assistant persona — then build the ingestion step that
chunks, embeds via `ollama_client.embed()`, and stores rows in
`knowledge`.