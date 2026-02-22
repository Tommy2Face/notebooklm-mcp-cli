# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**NotebookLM MCP Server & CLI** (v0.2.20) — Programmatic access to Google NotebookLM via both a Model Context Protocol server (29 tools) and a CLI (`nlm`). Uses reverse-engineered RPC API with cookie-based auth. Built with FastMCP + Typer + httpx.

Python >=3.11 | MIT License | Tested with personal/free tier accounts.

## Commands

```bash
# Install / reinstall after code changes (ALWAYS clean cache first)
uv tool install .
uv cache clean && uv tool install --force .

# Run MCP server
notebooklm-mcp                           # stdio (default)
notebooklm-mcp --debug                   # with debug logging
notebooklm-mcp --transport http --port 8000  # HTTP mode

# Run CLI
nlm notebook list
nlm --help

# Tests
uv run pytest                             # full suite
uv run pytest tests/test_file.py::test_function -v  # single test
uv run pytest -m e2e                      # e2e tests (needs NOTEBOOKLM_E2E=1)
uv run pytest -m integration              # integration tests

# Lint & type check
uv run ruff check src/ tests/             # linting (E, F, I, UP, B, SIM rules)
uv run ruff format src/ tests/            # formatting
uv run mypy src/                          # type checking (strict mode)

# Build Claude Desktop extension (.mcpb)
uv run python scripts/build_mcpb.py
```

## Architecture

### Core: Mixin-Based API Client

`NotebookLMClient` (`core/client.py`) composes `BaseClient` + 9 domain mixins via multiple inheritance:

```
BaseClient (core/base.py)          ← HTTP/RPC infrastructure, auth, batchexecute protocol
├── NotebookMixin (core/notebooks.py)   ← CRUD, configure chat, AI summary
├── SourceMixin (core/sources.py)       ← Add (URL/text/Drive/file), sync, delete, content
├── ConversationMixin (core/conversation.py) ← Query with conversation history
├── StudioMixin (core/studio.py)        ← Create audio/video/report/flashcards/slides/etc.
├── ResearchMixin (core/research.py)    ← Web/Drive research, poll, import
├── SharingMixin (core/sharing.py)      ← Public links, collaborator invites
├── DownloadMixin (core/download.py)    ← Download artifacts (audio/video/pdf/md/json)
├── ExportMixin (core/exports.py)       ← Export to Google Docs/Sheets
└── NotesMixin (core/notes.py)          ← Note CRUD
```

**When adding new API functionality:** create a new mixin or extend an existing one, then add it to `NotebookLMClient`'s inheritance chain.

### BaseClient (`core/base.py`)

- All NotebookLM RPC IDs are defined as class constants
- Handles cookie auth, CSRF token extraction, session ID management
- `_make_rpc_request()` — core method for all API calls via batchexecute
- Automatic auth recovery on 401/403 (re-fetches CSRF from page)
- `DEFAULT_TIMEOUT = 30.0s`, `SOURCE_ADD_TIMEOUT = 120.0s`

### MCP Server (`mcp/`)

- `mcp/server.py` — FastMCP instance, transport selection, health endpoint
- `mcp/tools/` — 29 tools split by domain (notebooks, sources, studio, research, chat, downloads, exports, notes, auth)
- `mcp/tools/_utils.py` — `@logged_tool()` decorator auto-registers tools into `_tool_registry`; `get_client()` returns cached singleton client
- Tool registration: `register_all_tools()` iterates `_tool_registry` and registers with FastMCP instance

**Environment variables:**
- `NOTEBOOKLM_MCP_TRANSPORT` — stdio (default), http, sse
- `NOTEBOOKLM_MCP_HOST`, `NOTEBOOKLM_MCP_PORT` — HTTP binding
- `NOTEBOOKLM_MCP_DEBUG` — debug logging
- `NOTEBOOKLM_QUERY_TIMEOUT` — query timeout (default 120s)

### CLI (`cli/`)

- `cli/main.py` — Typer app entry point (`nlm`), registers nested command groups
- `cli/commands/` — one module per domain (notebook, source, studio, research, chat, share, download, export, note, setup, doctor, etc.)
- `cli/formatters.py` — Rich-based output: `TableFormatter`, `JSONFormatter`, `QuietFormatter`
- `cli/commands/verbs.py` — verb-based wrappers (`nlm create`, `nlm list`, `nlm delete`)

### Key Patterns

- **Confirmation-required operations:** Delete, sync, and studio creation tools require `confirm=True`. Never bypass this.
- **Automatic retry:** `core/retry.py` — exponential backoff on 429/500/502/503/504. Max 3 retries.
- **Profile-based multi-account:** Storage in `~/.notebooklm-mcp-cli/profiles/<name>/auth.json`. CLI uses `--profile` flag. Auto-migrates from old `~/.notebooklm-mcp/` and `~/.nlm/` paths.
- **CodeMapper** (`core/constants.py`) — bidirectional code-to-name mapping used throughout for artifact types, chat goals, ownership, etc.

### Data Models

- `core/data_types.py` — internal dataclasses (Notebook, ConversationTurn, Collaborator, ShareStatus)
- `core/models.py` — Pydantic models for external API responses (Notebook, Source, Artifact, QueryResponse, etc.)
- `core/errors.py` — exception hierarchy rooted at `NotebookLMError` (ArtifactError, ClientAuthenticationError, etc.)
- `core/exceptions.py` — CLI-specific `NLMError` with `message` + `hint` fields

## Authentication

Cookie-based auth from Chrome DevTools. CSRF token and session ID are auto-extracted.

**Quick setup:** `save_auth_tokens(cookies=<cookie_header>)` or set `NOTEBOOKLM_COOKIES` env var.

**Fast setup:** Also pass `request_body` (CSRF) and `request_url` (session ID) from any batchexecute network request to skip the initial page fetch.

See `docs/AUTHENTICATION.md` for full details. When API calls fail with auth errors, re-extract fresh cookies.

## Contributing

When adding new features:

1. Capture the network request via Chrome DevTools
2. Document the RPC ID in `docs/API_REFERENCE.md`
3. Add the method to the appropriate mixin in `core/` (or create a new one)
4. Add the MCP tool in `mcp/tools/` using the `@logged_tool()` decorator
5. Add CLI command in `cli/commands/`
6. Add test cases

## Documentation

- `docs/API_REFERENCE.md` — RPC IDs, parameter structures, response formats (read when debugging API or adding features)
- `docs/MCP_GUIDE.md` — All 29 MCP tools with examples
- `docs/CLI_GUIDE.md` — Complete CLI command reference
- `docs/MCP_CLI_TEST_PLAN.md` — Step-by-step test cases for validation
