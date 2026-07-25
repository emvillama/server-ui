# Persona AI Hub — Phase 2 Development Log (Knowledge / RAG)

Status as of this document: **Phase 2 complete and confirmed live.**
Every item from the original Phase 2 handoff doc is built, tested, and
has now been confirmed working end-to-end against the real Ollama server
(not just mocks) — persona creation, real file upload (.pdf/.docx/.pptx),
extraction, chunking, embedding, retrieval-augmented `/chat`, and the
document-level view/delete management added after the original roadmap.

This log picks up where `P1_DevLog.md` left off. See that file for
request-flow diagrams and Phase 1 file-by-file summaries — not repeated
here.

## Project structure so far
```
server-ui/
├── .env                         # real config, gitignored
├── .env.example                 # config template, committed
├── .gitignore
├── P1_DevLog.md
├── P2_DevLog.md                 # this file
├── README.md
├── requirements.txt              # UPDATED — pypdf, python-docx, python-pptx, python-multipart
├── backend/
│   ├── __init__.py
│   ├── config.py                 # UPDATED — added embedding_model
│   ├── database.py                # UPDATED — SQLite FK enforcement fix
│   ├── main.py                     # UPDATED — registers knowledge router
│   ├── models/
│   │   ├── __init__.py            # UPDATED — registers Knowledge
│   │   ├── persona.py
│   │   └── knowledge.py           # NEW — the `knowledge` table
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   ├── persona.py
│   │   └── knowledge.py            # NEW — ingest/upload request + response shapes
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   ├── health.py
│   │   ├── personas.py
│   │   └── knowledge.py             # NEW — ingest (text + file upload), list, delete
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ollama_client.py        # UPDATED — added embed()
│   │   ├── persona_service.py       # UPDATED — run_chat() wires in retrieval
│   │   ├── chunking.py               # NEW — chunk_text()
│   │   ├── similarity.py              # NEW — cosine_similarity()
│   │   ├── file_extraction.py          # NEW — extract_text() for txt/md/pdf/docx/pptx
│   │   └── knowledge_service.py         # NEW — ingest/search/list/delete
│   └── deploy/                  # still empty — systemd unit not built yet
├── frontend/                    # still empty
├── data/                        # SQLite file lands here, gitignored
└── tests/
    ├── conftest.py                # UPDATED — added shared `db` fixture
    ├── test_health.py
    ├── test_personas.py
    ├── test_chat.py
    ├── test_chunking.py
    ├── test_similarity.py           # NEW
    ├── test_file_extraction.py       # NEW
    ├── test_knowledge_service.py
    ├── test_search_knowledge.py
    ├── test_run_chat_knowledge.py
    └── test_knowledge_endpoint.py    # UPDATED — merged in upload/list/delete tests
```

## Context carried over from Phase 1

- Development still happens on a personal computer, not the AMD server.
  `OLLAMA_HOST` in `.env` still points at the server's LAN IP
  (`192.168.1.240:11434`).
- Architectural conventions from Phase 1 continue to apply: routers stay
  thin, services raise plain Python exceptions (not HTTP errors),
  `ollama_client.py` is the only file allowed to call Ollama's HTTP API,
  Pydantic schemas stay separate from SQLAlchemy models, JSON columns for
  flexible/evolving data, tests mock `ollama_client` functions via
  `monkeypatch` rather than requiring a live Ollama connection.

## Milestone: Configuration — `embedding_model`
Added `embedding_model: str = "nomic-embed-text"` to `Settings` in
`config.py`, alongside the existing `default_model`. Same reasoning as
every other setting there: centralize the model name in one place rather
than hardcoding it wherever `embed()` gets called. Confirmed
`nomic-embed-text` was already pulled on the server (`ollama list`)
before writing any code — the Phase 2 equivalent of Phase 1's
`OLLAMA_HOST` connectivity check.
 
Deliberately did **not** add a dedicated test asserting this default —
a static string assignment with no branching or logic behind it. Noted
as a deliberate skip, not an oversight.

## Milestone: Ollama client — `embed()`
Added `embed(model, text) -> list[float]` to `ollama_client.py`, mirroring
`chat()`'s structure exactly: same `httpx.AsyncClient` setup, same
`OllamaError` wrapping. Takes one string in, one vector out — no
batching, since Ollama's `/api/embeddings` only takes a single `prompt`
at a time.
 
## Milestone: Data model — the `knowledge` table
`models/knowledge.py`: one row per chunk of a source document, embedded
and attached to a single persona. Three design decisions made explicitly
before writing this, since they weren't obvious defaults:
 
- **Single-persona ownership** (`persona_id` foreign key, no join table)
  — each persona does a wildly different job, so cross-persona sharing
  isn't a real need.
- **Embedding stored as a JSON column**, not a separate vector table or
  SQLite extension — a plain Python loop over rows for cosine similarity
  is fast enough at personal scale.
- **Chunking granularity deferred** to the next component below — the
  table schema doesn't care how a chunk was produced.
Fields: `id`, `persona_id` (FK, `ondelete="CASCADE"`), `source_filename`,
`chunk_index`, `chunk_text`, `embedding` (JSON list of floats),
`created_at`. First use of a SQLAlchemy `relationship()` in this codebase
— `persona.knowledge_chunks`.
 
## Milestone: Chunking — `chunk_text()`
Discussed three strategies explicitly (fixed-size, paragraph-based,
fixed-size-with-sentence-boundary-awareness) before implementing. Chose
the sentence-boundary-aware compromise: predictable chunk sizes like
fixed-size, but avoids cutting mid-sentence, and doesn't depend on how
cleanly the source notes happen to be formatted (unlike paragraph-based).
 
`services/chunking.py`: `chunk_text(text, target_size=500, max_search=200)`
searches up to `max_search` characters past the target for a
sentence-ending boundary to cut on, falling back to the nearest word
boundary if none is found nearby. (See Bugs & Fixes below for the
mid-word-cut issue this fallback originally had.)
 
## Milestone: Ingestion — `ingest_document()`
`services/knowledge_service.py`: chunks the text via `chunk_text()`,
embeds each chunk via `ollama_client.embed()`, stores one `Knowledge` row
per chunk. Reuses `get_persona()` from `persona_service.py` for the
missing-persona check. Commits once after the full loop, not per-chunk,
so a failure partway through rolls back the whole ingestion rather than
leaving a half-embedded document. (See Bugs & Fixes below for two real
bugs this surfaced in `database.py`.)
 
## Milestone: Retrieval — `cosine_similarity()` + `search_knowledge()`
`services/similarity.py`: `cosine_similarity(a, b)` — pure math, no I/O,
kept separate for isolated testability (same reasoning as `chunking.py`).
 
`search_knowledge()` in `knowledge_service.py`: embeds a query, compares
it against every stored chunk for a persona via `cosine_similarity()`,
returns the top N matches (default 5). Plain Python loop over rows — fine
at personal scale per the original Phase 2 handoff notes.
 
## Milestone: Retrieval wired into `/chat`
`persona_service.py`'s `run_chat()`: before assembling messages, does a
cheap "does this persona have any knowledge rows at all" check. Only if
true does it embed the incoming message and call `search_knowledge()`,
injecting the top matches as an additional system message (labeled with
source filenames) before the conversation history and the user's message.
The existence check avoids an extra Ollama call on every single message
for personas that never have knowledge attached (D&D GM, Recipe
Recommender, etc.).
 
Importing `knowledge_service` from inside `run_chat()` (not at the top of
`persona_service.py`) is deliberate — `knowledge_service.py` imports
`get_persona` from `persona_service.py`, so a top-level import the other
way would create a circular import. By the time `run_chat()` actually
executes, both modules are already loaded, so the local import avoids the
cycle.
 
## Milestone: `/knowledge` endpoint — raw text ingestion
`routers/knowledge.py`: `POST /personas/{persona_id}/knowledge` accepting
raw pasted text (`source_filename` + `text`). First version of this
router — file upload came later (component 10 below).
 
## Milestone: File extraction — `.txt`, `.md`, `.pdf`, `.docx`, `.pptx`
Before building, decided the supported format set explicitly, since the
real target is actual university notes, not just plain text:
 
- **Supported**: `.pdf`, `.docx`, `.pptx` (what the real notes are in),
  plus `.txt`/`.md` since those are free (no library needed).
- **Explicitly not supported**: legacy binary Office formats (`.doc`,
  `.ppt`) — the standard libraries (`python-docx`, `python-pptx`) only
  read the modern XML-based formats.
- **Scanned/image-only PDFs**: produce no extractable text, which raises
  a clear error rather than silently creating a persona that "knows" an
  empty document. OCR is out of scope.
`services/file_extraction.py`: `extract_text(filename, content: bytes)`
dispatches to a per-format helper by extension. Raises
`UnsupportedFileTypeError` for anything outside the supported set, and
`EmptyExtractionError` if extraction succeeds but produces no usable
text.
 
Verified against **real generated files**, not just fakes — built actual
`.docx`/`.pptx` files via `python-docx`/`python-pptx` and a real `.pdf`
via `reportlab`, then confirmed extraction pulled the right content out
of each before calling this done.
 
## Milestone: File upload endpoint
`routers/knowledge.py`: added `POST /personas/{persona_id}/knowledge/upload`
alongside the existing raw-text endpoint (kept both — raw text stays
useful for quick testing without a file). Accepts a multipart
`UploadFile`, calls `extract_text()`, then `ingest_document()`. Requires
`python-multipart` as a dependency for FastAPI's file upload support.
 
## Milestone: Overwrite-on-reingest
Decided explicitly: re-ingesting a document under a filename already
ingested for that persona **overwrites** (deletes old chunks, inserts
new ones) rather than duplicating or rejecting. Silent duplication would
actively degrade retrieval quality as notes get edited and re-uploaded —
the realistic, frequent workflow here.
 
`ingest_document()` updated to delete any existing `Knowledge` rows for
that `(persona_id, source_filename)` pair before inserting the new
chunks, inside the same try/except as the rest of the function, with an
explicit `db.rollback()` on failure — so a failed re-ingest restores the
old chunks rather than leaving the document half-replaced.
 
## Milestone: View and delete knowledge, by document
Decided explicitly to show knowledge **grouped by document** (one entry
per `source_filename` with a chunk count and last-ingested timestamp),
not as a flat list of raw chunks — matches how a person actually thinks
about "what has this persona ingested."
 
- `list_documents(db, persona_id)` — `GROUP BY source_filename` query,
  returns `chunk_count` and `ingested_at` per document.
- `delete_document(db, persona_id, source_filename)` — deletes every
  chunk for that filename; raises `KnowledgeNotFoundError` if nothing
  matched (distinct from `PersonaNotFoundError`).
- `schemas/knowledge.py`: added `DocumentSummaryOut`.
- `routers/knowledge.py`: added `GET` (list) and `DELETE` (remove one
  document), both mapping `PersonaNotFoundError` → `404`; delete also
  maps `KnowledgeNotFoundError` → `404`.
**Known limitation, flagged rather than fixed:** `source_filename` sits
directly in the URL path for the delete route — a filename containing a
`/` would break the route. Unlikely for typical uploaded filenames, so
left as-is.
 
## Milestone: Test suite refactor
Reviewing all test files together (rather than one at a time) surfaced
real duplication:
 
- `client`/`persona` fixtures, already shared via `conftest.py`, had been
  redefined locally in two files — an artifact of having been built in
  an isolated sandbox without the real `conftest.py` in scope.
- An identical `db` fixture was duplicated three times across
  `test_knowledge_service.py`, `test_run_chat_knowledge.py`, and
  `test_search_knowledge.py`. Moved into `conftest.py` as a shared
  fixture.
- One file mixed two concerns — pure `extract_text()` logic tests
  bundled with `/knowledge` HTTP endpoint tests, inconsistent with the
  established one-file-per-concern pattern. Split into
  `test_file_extraction.py` (pure logic) and merged the endpoint tests
  into `test_knowledge_endpoint.py`.
- Inconsistent mocking style (an `autouse` fixture in one file vs.
  manual per-test `monkeypatch` everywhere else) — converted to match
  the existing style.
Net result: same 59 total tests, purely a duplication/consistency
cleanup, zero new coverage added.
 
## Milestone: Live end-to-end confirmation
Every automated test mocks `ollama_client.embed()`/`chat()` — correct
for the suite, but Phase 1 didn't consider itself done until a real
round-trip was confirmed against the actual Ollama server, and Phase 2
hadn't had that moment yet. Ran the full flow manually via Swagger UI
against the real server: health check, persona creation, real file
upload, list confirmation, a `/chat` message that correctly reflected the
uploaded notes' content, and a re-upload confirming overwrite behavior
held at the real-database level, not just in SQLite-backed tests.
 
**Result: everything worked as intended on the first live run.** No bugs
surfaced that the mocked test suite hadn't already caught.
 
## Bugs found and fixed
 
**1. Chunking fallback could cut a word in half.**
Found by manually eyeballing `chunk_text()`'s output against a realistic
paragraph, not by the first round of automated tests — those only used
short, uniform sentences that never exercised the fallback path. When no
sentence boundary was found near the target cut point, the original hard
character-count fallback could land mid-word (e.g. "...as it fo" /
"rms the base..."). Fixed by changing the fallback to cut at the nearest
word boundary (last space) instead, only falling back to a true hard cut
if there's no space to find at all. Locked in with a dedicated regression
test using punctuation-free text.
 
**2. `ondelete="CASCADE"` was silently non-functional.**
SQLite doesn't enforce foreign keys by default, and nothing in
`database.py` turned that on — so deleting a persona with attached
knowledge threw an `IntegrityError` instead of cascading. Fixed by
registering a `PRAGMA foreign_keys=ON` event listener on SQLAlchemy's
`Engine` *class* (not a specific instance) — needed at the class level
specifically because `tests/conftest.py` builds its own separate engine
per test, independent of the app's main `engine` object.
 
**3. A second, subtler layer of the same bug, at the ORM level.**
Even with the DB-level pragma on, SQLAlchemy's own unit-of-work would
still null out an *already-loaded* child collection itself, bypassing the
database's `ON DELETE CASCADE` entirely. Caught because an early version
of the cascade-delete test accessed `persona.knowledge_chunks` right
before deleting the persona. Fixed with `passive_deletes=True` on the
`Persona.knowledge_chunks` backref. Confirmed via a throwaway script that
this only matters for an *unloaded* collection, then rewrote the test to
match how `delete_persona()` is actually called from the router (which
never touches `knowledge_chunks` first) rather than testing an edge case
that doesn't occur in real usage.
 
**4. `NameError: name 'backref' is not defined`.**
Surfaced only when actually run against the real project — the
`passive_deletes` fix (bug #3) required
`from sqlalchemy.orm import relationship, backref`, but only
`relationship` had been imported. One-line fix.
 
**5. New test file not discovered by pytest.**
`tests/test_knowledge_service.py` had been saved as
`tests/test_knowledge_service` (no `.py` extension), so pytest's
`test_*.py` discovery pattern silently never matched it — no error, the
file just didn't show up in the collected test list. Renamed with the
extension added.
 
**6. `ModuleNotFoundError: No module named 'docx'` on server startup.**
The new file-extraction libraries (`python-docx`, `python-pptx`, `pypdf`,
`python-multipart`) had been added to `requirements.txt` but hadn't
actually been `pip install`ed into the venv yet. Fixed with a plain
`pip install` of all four inside the activated venv.

## Not built yet
- OCR for scanned/image-only PDFs — file extraction works for real text
  layers, but a scanned/image-only PDF produces no extractable text and
  currently just raises a clear error rather than being handled
- URL-encoding handling for filenames containing special characters in
  the delete route — a filename with a `/` would break the route;
  flagged as a known limitation rather than fixed

## Next immediate step
Phase 2 is functionally complete and live-confirmed. Next up: Phase 3
(Tools), starting narrow with a single low-risk tool given `llama3.1:8b`'s 
known fragility with structured tool-calling output.