# Persona AI Hub — Backend Development Log

Status as of this document: **Phase 1 (Backend foundation) functionally
complete.** Full persona CRUD and a working `/chat` endpoint have been
tested end-to-end against Ollama running on the server. Not yet built:
the systemd unit for persistent deployment, tests, and the frontend.

Development is happening on a personal computer, not the AMD server that
hosts Ollama. The backend reaches Ollama over the LAN at
`192.168.1.240:11434`. When the backend eventually moves to the server
itself, `.env` will need `OLLAMA_HOST` updated to `localhost`, and the
SQLite database will start fresh there (personas created during dev won't
carry over automatically).

## Project structure so far

```
server-ui/
├── .env                         # real config, gitignored
├── .env.example                 # config template, committed
├── .gitignore
├── DevLog.md
├── README.md
├── requirements.txt
├── backend/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── main.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── persona.py
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
│   │   ├── ollama_client.py
│   │   └── persona_service.py
│   └── deploy/                  # empty so far — systemd unit not built yet
├── frontend/                    # empty so far
├── data/                        # SQLite file lands here, gitignored
└── tests/                       # empty so far — no tests written yet
```

Note: every package folder under `backend/` also grows a `__pycache__/`
during normal use (Python-generated, gitignored, safe to ignore/delete
anytime — not listed above since it's not source code).

## Request flow: POST /chat

A full round-trip through every layer, for reference:

1. **Client** sends `POST /chat` with `persona_id`, `message`, and optional
   `history`.
2. **`routers/chat.py`** parses the request into a `ChatRequest`, calls
   `persona_service.run_chat()`, and is responsible only for translating
   whatever comes back (or whatever exception is raised) into an HTTP
   response.
3. **`persona_service.run_chat()`** is the orchestrator:
   - Calls `get_persona()` to pull the persona row from SQLite by id —
     raises `PersonaNotFoundError` if it doesn't exist (→ `404` at the
     router).
   - Assembles the message list: the persona's `system_prompt` first (if
     set), then `history`, then the new `message`.
4. **`ollama_client.chat()`** takes that message list plus the persona's
   `model` (or `settings.default_model` as fallback) and `params`, and
   POSTs to Ollama's `/api/chat` over the LAN (`192.168.1.240:11434`) with
   `stream: False`.
5. **Ollama** generates the reply and returns it as a single JSON response.
6. The reply text flows back up: `ollama_client.chat()` returns it to
   `run_chat()`, which returns `(reply, model)` to the router, which wraps
   it in a `ChatResponse` and sends it to the client.

Failure modes are handled at the router boundary: `PersonaNotFoundError` →
`404`, `OllamaError` (unreachable server, bad HTTP status, or unexpected
response shape from Ollama) → `502`, since a failure at that stage is
Ollama's fault, not this server's.

## File-by-file summary

### `.env` / `.env.example`
Configuration values the app reads at startup: `OLLAMA_HOST`,
`DEFAULT_MODEL`, `DB_PATH`, `OLLAMA_TIMEOUT`. `.env.example` is a generic,
committed template; `.env` holds the real values for this machine (right
now, `OLLAMA_HOST=http://192.168.1.240:11434` to reach the server over the
LAN) and will be gitignored once `.gitignore` exists. Nothing secret in
either file currently — Ollama has no auth — but the split is a habit worth
keeping for when that changes.

### `requirements.txt`
Every Python package the project depends on: FastAPI (web framework),
Uvicorn (the server that runs it), SQLAlchemy (ORM/database layer),
Pydantic + pydantic-settings (data validation and config loading), httpx
(calls Ollama's HTTP API, and powers FastAPI's `TestClient` in tests),
python-dotenv (parses `.env`), pytest + pytest-asyncio (the test suite —
see the PUT-fix milestone below).

### `backend/config.py`
The *only* file that reads environment variables directly. Defines a
`Settings` class (via `pydantic-settings`) with typed fields and sensible
defaults, then instantiates one shared `settings` object. Every other file
that needs a config value imports this: `from backend.config import
settings`. Centralizing it here means no hostnames or paths are hardcoded
elsewhere in the codebase.

### `backend/database.py`
Sets up the actual SQLite connection: an `engine` pointed at the file path
from `settings.db_path`, a `SessionLocal` factory for creating database
sessions, and a shared `Base` class that every table definition inherits
from. Also defines `get_db()`, a generator function FastAPI uses to hand a
fresh database session to each request and guarantee it gets closed
afterward, even if the request errors.

### `backend/models/persona.py`
The SQLAlchemy definition of the `personas` table — this is what
determines the actual columns in the SQLite database. Fields: `id`, unique
`name`, `system_prompt` (long text), `params` (JSON — mirrors Ollama's
native `options` dict: temperature, top_p, etc.), `capabilities` (JSON —
feature flags like vision/tools/knowledge, meaningful starting in Phase 5),
optional `model` override, and `created_at`/`updated_at` timestamps.
`params` and `capabilities` are stored as JSON blobs rather than individual
columns specifically so new fields can be added later without a database
migration.

### `backend/models/__init__.py`
One line: `from backend.models.persona import Persona`. This ensures the
`Persona` table is "registered" with `Base` as soon as `backend.models` is
imported anywhere — which matters because `Base.metadata.create_all()` (in
`main.py`) only creates tables for models it knows have been imported.
Future tables (knowledge, tools, skills) will get added here the same way.

### `backend/schemas/persona.py`
Pydantic classes defining what the future `/personas` API actually accepts
and returns — deliberately separate from the SQLAlchemy model above, since
the API contract and the storage layout are allowed to diverge.
- `OllamaParams` / `Capabilities` — small reusable validated shapes for the
  `params`/`capabilities` JSON blobs, with every field optional/defaulted
  and `extra="allow"` so new keys don't break validation.
- `PersonaCreate` — request body shape for creating a persona (`name`
  required, everything else optional).
- `PersonaUpdate` — request body shape for editing a persona (everything
  optional, so a PUT only touches fields actually sent).
- `PersonaOut` — response shape sent back to the client;
  `from_attributes=True` is what lets this be built directly from a
  SQLAlchemy `Persona` row rather than a plain dict.

### `backend/routers/health.py`
`GET /health`. Now checks Ollama reachability via
`ollama_client.is_reachable()` (added in the chat-endpoint milestone below)
and returns `{"status": "ok", "ollama_reachable": true/false}`. Useful as a
first check whenever something seems broken — if this shows `false`, the
issue is network/server-side, not this codebase (see the chat-endpoint
milestone notes for a real example of this).

### `backend/main.py`
The actual FastAPI application entrypoint — what `uvicorn` runs. Defines a
`lifespan` function that runs `Base.metadata.create_all(bind=engine)` on
startup, which is the line that physically creates the `personas` table in
the SQLite file the first time the app runs. Imports `backend.models` to
make sure `Persona` is registered before that happens. Registers the
health router via `app.include_router(health.router)` — every future
router (personas, chat) gets added here the same way.

### `backend/services/__init__.py`
Currently empty. This package will hold orchestration logic: a client for
calling Ollama's API (`ollama_client.py`) and the persona business logic
(`persona_service.py`) — keeping that logic out of the router files, which
should stay thin (parse request → call a service function → return
result).

## Milestone: app runs successfully
`uvicorn backend.main:app --reload` starts cleanly and
`curl http://localhost:8000/health` returns `{"status":"ok"}`. Confirms
config loading, database setup, and routing all work together correctly.

Setup snags along the way, worth remembering:
- `requirements.txt` needs to be an actual saved file, not just content
  shown in chat — install with `pip install -r requirements.txt` inside an
  **activated** virtual environment (prompt should show `(venv)`).
- Ended up with two virtual environments (`venv` and an accidental `.venv`)
  from an earlier attempt. Deleting `.venv` through VS Code's file explorer
  failed with `ENOTEMPTY` — a file watcher or terminal likely still had a
  handle open inside it. Fixed by deleting from the terminal directly
  (`rm -rf .venv`), which doesn't have that race condition. Only `venv/` is
  kept going forward.
- `backend/__pycache__/` appeared automatically the first time the app ran
  — this is normal, Python-managed, and safe to delete any time
  (`rm -rf backend/__pycache__`). Now excluded via `.gitignore`, along with
  `venv/`, `.venv/`, `.env`, and the SQLite db file, so none of that ever
  gets committed.

## Milestone: persona CRUD working
`backend/services/persona_service.py` and `backend/routers/personas.py`
built and wired into `main.py`. Tested via Swagger UI at `/docs`:
`POST /personas` with a minimal body (just `name` + `system_prompt`)
returned `201` with the full persona object, including auto-generated
`id` and timestamps. First real persona created: "General Chatbot".

### `backend/services/persona_service.py`
The actual database logic for personas: `list_personas`, `get_persona`,
`create_persona`, `update_persona`, `delete_persona`. Deliberately knows
nothing about HTTP — raises plain Python exceptions
(`PersonaNotFoundError`, `PersonaNameConflictError`) rather than dealing in
status codes, so this logic isn't tied to being used behind a web API. Uses
`.model_dump(exclude_none=True)` when converting the `OllamaParams` schema
to a plain dict for storage, so unset fields don't get stored as explicit
`null`s. Calls `db.commit()` then `db.refresh()` after writes so the
returned object reflects database-generated values like timestamps.

### `backend/routers/personas.py`
The actual `/personas` endpoints (`GET`, `POST`, `GET /{id}`, `PUT /{id}`,
`DELETE /{id}`). Deliberately thin — each function calls the matching
service function and translates its exceptions into HTTP status codes
(404 for not found, 409 for name conflicts). Uses `Depends(get_db)` to get
a database session per request, and `response_model=PersonaOut` so
responses are validated against the schema from step 5 before being sent.

## Milestone: chat endpoint built, health check confirms Ollama reachable
Built `backend/schemas/chat.py` (request/response shapes),
`backend/services/ollama_client.py` (the only file that calls Ollama's
HTTP API directly), added `run_chat()` to `persona_service.py` (assembles
persona system prompt + history + new message, calls Ollama, returns the
reply), and `backend/routers/chat.py` (`POST /chat`). Also upgraded
`/health` to actually check Ollama reachability via
`ollama_client.is_reachable()` rather than just returning a static OK.

`/health` briefly showed `"ollama_reachable": false` after this change —
turned out to simply be the server (192.168.1.240) being powered off at
the time, not a bug. Good reminder for this dev setup specifically: since
the backend runs on a personal computer separate from the AI server,
`ollama_reachable: false` should prompt checking "is the server actually
on" before assuming a config/network problem.

### `backend/schemas/chat.py`
`ChatMessage` (role + content), `ChatRequest` (persona_id, message, and
optional `history` of prior turns), `ChatResponse` (persona_id, reply,
model used). `history` exists because Ollama is stateless — the full
conversation has to be resent every call; nothing persists it server-side
yet.

### `backend/services/ollama_client.py`
The only file allowed to make HTTP calls to Ollama. `chat()` posts to
`/api/chat` with `stream: False` (full reply at once, not token-by-token)
and returns just the reply text. `is_reachable()` does a lightweight check
against `/api/tags`, used by `/health`. Both wrap failures in a single
custom `OllamaError` exception, covering unreachable server, HTTP errors
from Ollama, and unexpected response shapes.

### `run_chat()` in `backend/services/persona_service.py`
Pulls a persona from the DB, prepends its `system_prompt` as the first
message (only if one is set), appends conversation history and the new
user message, then calls `ollama_client.chat()` using the persona's
`params` as Ollama's generation options and `persona.model or
settings.default_model` as the model. This is the function that makes
per-persona tuning (system prompt, temperature, model override) actually
take effect.

### `backend/routers/chat.py`
`POST /chat`. Thin, same pattern as the personas router — calls
`run_chat()`, translates `PersonaNotFoundError` to `404` and `OllamaError`
to `502` (upstream failure, not this server's fault).

## Not built yet
- `backend/deploy/persona-ai-hub.service` (systemd unit)

## Next immediate step
Test a full chat round-trip via `/docs` — `POST /chat` with a real
`persona_id` and message, confirm an actual Ollama-generated reply comes
back. Then move to the systemd unit for running this as a service on the
server.

## Milestone: full chat round-trip confirmed working end-to-end
`POST /chat` successfully returned a real Ollama-generated reply. First
attempt hit a `502` — persona's `model` field had been saved as the
literal string `"string"` (Swagger's unedited placeholder text in the
request body), so Ollama correctly rejected it with
`model 'string' not found`. Fixed by deleting and recreating the persona
with that field either omitted entirely or set to a real model name.

Noted gap for later, not urgent: `PUT /personas/{id}` currently can't
distinguish "field omitted, don't touch it" from "field explicitly set to
null, clear it" — both arrive as `None`. Not a problem yet since
delete-and-recreate works fine for testing, but worth a real fix if
editing personas becomes a frequent workflow.

This confirms the full path: persona config in SQLite → assembled into a
system prompt + message list → sent to Ollama on the server (192.168.1.240)
over the LAN → real model reply returned through the API. Core of Phase 1
is functionally complete.

## Not built yet
- `backend/deploy/persona-ai-hub.service` (systemd unit)
- Frontend

## Milestone: PUT null-vs-omitted bug fixed, test suite added
Fixed the gap noted above: `update_persona()` now uses Pydantic's
`data.model_fields_set` to tell "field omitted from the request" apart
from "field explicitly sent as `null`" — previously both looked identical
(`None`) once the request body was parsed.

- `model` is the one genuinely nullable column, so explicitly sending
  `"model": null` now correctly clears a persona's model override back to
  `settings.default_model`. Omitting `model` from the request leaves it
  untouched, as it always should have.
- `name`, `system_prompt`, `params`, and `capabilities` are non-nullable
  columns. Explicitly sending `null` for any of those now raises a new
  `PersonaValidationError`, mapped to HTTP `422` in the router — a clear
  error instead of the field being silently left alone.

Added a full pytest suite: `tests/conftest.py` (isolated temp-SQLite
database per test via a `get_db` dependency override, plus a reusable
`persona` fixture), `tests/test_health.py`, `tests/test_personas.py`
(CRUD + all four PUT edge cases above, explicitly), and
`tests/test_chat.py` (Ollama calls mocked via `monkeypatch`, so these
don't depend on the server being reachable — includes a test asserting
the persona's system prompt is actually the first message sent to
Ollama). `pytest.ini` added at the project root (`pythonpath = .`) so
tests can import `backend` correctly.

All 16 tests passing.

## Next immediate step
Either the systemd unit (`backend/deploy/persona-ai-hub.service`) — though
that may be worth deferring until closer to actual server deployment,
since development is still happening on a personal computer — or seeding
the remaining four personas from the roadmap (Coding Assistant, D&D Game
Master, Recipe Recommender, Second Brain/Study Assistant).