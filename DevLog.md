# Persona AI Hub — Backend Development Log

Status as of this document: **Phase 1 (Backend foundation), steps 1–6
complete.** The app runs, has a working `/health` endpoint, and has a
`personas` table defined and wired up to auto-create on startup — but no
CRUD endpoints or chat endpoint yet. Those are next.

Development is happening on a personal computer, not the AMD server that
hosts Ollama. The backend reaches Ollama over the LAN at
`192.168.1.240:11434`, confirmed working via `curl .../api/tags`. When the
backend eventually moves to the server itself, `.env` will need
`OLLAMA_HOST` updated to `localhost`, and the SQLite database will start
fresh there (personas created during dev won't carry over automatically).

## Project structure so far

```
persona-ai-hub/
├── .env                        # real config, gitignored (not created yet: .gitignore)
├── .env.example                # config template, committed
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
│   │   └── persona.py
│   ├── routers/
│   │   ├── __init__.py
│   │   └── health.py
│   ├── services/               # empty so far — Phase step 7–8
│   │   └── __init__.py
│   └── deploy/                 # empty so far — systemd unit comes later
├── frontend/                   # empty so far
├── data/
│   └── .gitkeep                # SQLite file will land here, gitignored
└── tests/                      # empty so far
```

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
(will be used to call Ollama's API), python-dotenv (parses `.env`), pytest
(testing, later).

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
One endpoint, `GET /health`, currently returning a static
`{"status": "ok"}`. Deliberately minimal for now — no Ollama reachability
check yet, since that depends on the Ollama client file that doesn't exist
yet (upcoming step). Will be upgraded once that's built.

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

## Not built yet
- `backend/routers/personas.py` + persona CRUD service logic
- `backend/services/ollama_client.py` (the actual Ollama HTTP calls)
- `backend/routers/chat.py` + chat orchestration
- `.gitignore`
- `backend/deploy/persona-ai-hub.service` (systemd unit)
- Any tests
- Frontend

## Next immediate step
Run the app for the first time:
```bash
uvicorn backend.main:app --reload
curl http://localhost:8000/health
```
Confirm `{"status":"ok"}` comes back and that the SQLite file
(`data/persona_hub.db`) gets created with a `personas` table. Then move to
building out full CRUD for personas.