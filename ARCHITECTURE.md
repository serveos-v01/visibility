# Visibility — Master Architecture and Development Prompt

## 0. Instruction to Qwen Coder

You are a senior Python engineer, systems architect, and AI integration expert.

Your task is to build an open-source project named **Visibility**.

This document is the single source of truth.

Read the full document first, then implement the project step by step.

Rules:

- Do not add features outside this document.
- Do not create a web dashboard.
- Do not add cloud services.
- Do not add authentication.
- Do not add unnecessary files.
- Do not use runtime external dependencies.
- Use Python 3.9+ standard library only.
- Use pytest only as a dev dependency.
- All SDK output must be JSON-serializable.
- All CLI output must be strict JSON.
- Keep the architecture modular, clean, and easy to extend.
- If the response limit is reached, stop at the end of the current phase and wait for the user to say "continue".

---

# 1. Product Vision

Project name:

```txt
Visibility
```

Repository:

```txt
serveos-v01/visibility
```

One-line positioning:

```txt
A local-first, agent-ready observability, audit, and cost-guardrail SDK for AI agents and LLM applications.
```

Core idea:

Visibility helps developers and AI agents track:

- API requests
- errors
- LLM calls
- token usage
- estimated cost
- budget usage
- custom events
- agent actions
- tool usage
- session activity

Visibility must be usable by:

- human developers
- scripts
- CLI automation
- AI agents
- LLM wrappers
- agent frameworks

The most important design principle:

```txt
Visibility must be machine-readable first, human-readable second.
```

---

# 2. Target Users

Primary users:

1. Developers building LLM apps.
2. Developers building autonomous agents.
3. Teams needing local audit trails.
4. Developers needing lightweight cost tracking.
5. AI agents that need to inspect their own actions.

Example users:

- OpenAI wrapper developers
- LangChain users
- AutoGen users
- CrewAI users
- FastAPI AI backend developers
- local AI automation developers

---

# 3. Core Problem

Existing observability tools are often:

- too heavy
- dashboard-focused
- cloud-dependent
- hard to integrate
- not agent-friendly
- not machine-readable by default
- difficult to use in autonomous pipelines

Visibility must solve this by being:

- lightweight
- local-first
- zero-config
- strict JSON
- agent-ready
- schema-driven
- CLI-friendly
- easy to embed

---

# 4. Product Requirements

## 4.1 Must-have features

Visibility Version 1 must include:

1. Python SDK
2. local SQLite storage
3. strict JSON event model
4. request tracking
5. error tracking
6. LLM/token usage tracking
7. estimated cost tracking
8. budget guardrails
9. event query API
10. summary report API
11. secret redaction
12. plugin architecture
13. CLI
14. OpenAI-compatible tool schema
15. MCP-style manifest
16. examples
17. tests
18. GitHub Actions CI

---

## 4.2 Non-goals for Version 1

Do not build:

- web dashboard
- hosted SaaS
- user accounts
- remote database requirement
- TypeScript SDK yet
- GraphQL API
- complex UI
- metric visualization
- multi-tenant system
- plugin marketplace
- external service dependency

---

# 5. Tech Stack Decision

## Primary stack

```txt
Python 3.9+
```

## Runtime dependencies

```txt
None
```

Use only Python standard library.

## Dev dependency

```txt
pytest
```

## Storage

Default:

```txt
SQLite
```

Default path:

```txt
.visibility/visibility.db
```

## Why Python first?

Python is the primary language for:

- AI agents
- LLM apps
- OpenAI integrations
- LangChain
- AutoGen
- AI automation
- data pipelines

Therefore Python-first gives the highest chance of real adoption.

## Future TypeScript strategy

Do not build TypeScript SDK now.

Later, create a TypeScript SDK using the same:

- event schema
- tool schema
- storage behavior
- summary behavior
- CLI behavior

The `/spec` folder will be the shared contract.

---

# 6. Repository Structure

Create this structure:

```txt
visibility/
├─ .github/
│  └─ workflows/
│     └─ ci.yml
├─ docs/
│  └─ AGENT.md
├─ examples/
│  ├─ agent_tool.py
│  └─ basic.py
├─ spec/
│  ├─ event.schema.json
│  └─ tool.schema.json
├─ src/
│  └─ visibility/
│     ├─ __init__.py
│     ├─ cli.py
│     ├─ config.py
│     ├─ events.py
│     ├─ plugins.py
│     ├─ redact.py
│     ├─ schemas.py
│     ├─ storage.py
│     ├─ summary.py
│     └─ tracker.py
├─ tests/
│  ├─ test_events.py
│  ├─ test_redact.py
│  ├─ test_storage.py
│  ├─ test_summary.py
│  └─ test_tracker.py
├─ .gitignore
├─ LICENSE
├─ README.md
└─ pyproject.toml
```

Do not create extra top-level folders unless necessary.

---

# 7. Core Product Behavior

## 7.1 Simple SDK usage

The SDK must be usable in 2-4 lines:

```python
from visibility import Visibility

v = Visibility(service_name="my-agent")

v.track_llm(
    name="openai.chat",
    provider="openai",
    model="gpt-4o-mini",
    prompt_tokens=800,
    completion_tokens=200
)

print(v.summary())
```

## 7.2 Agent-ready usage

An AI agent should be able to call Visibility through a tool-call-like input:

```python
from visibility import execute_tool_call

result = execute_tool_call({
    "tool": "visibility_track",
    "arguments": {
        "type": "llm",
        "name": "openai.chat",
        "llm": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "prompt_tokens": 800,
            "completion_tokens": 200
        }
    }
})
```

## 7.3 CLI usage

The CLI must support:

```bash
visibility schema
```

```bash
visibility track --json '{"type":"custom","name":"demo.event"}'
```

```bash
visibility query --type=llm --limit=20
```

```bash
visibility summary
```

All CLI output must be strict JSON.

---

# 8. Event Data Contract

Every event must be a JSON-serializable dictionary.

Required fields:

```json
{
  "id": "uuid4-string",
  "timestamp": "UTC ISO 8601 string",
  "type": "request | error | llm | metric | trace | budget | custom",
  "name": "stable event name",
  "level": "debug | info | warn | error",
  "status": "success | failure | null",
  "duration_ms": "number | null",
  "request": "object | null",
  "error": "object | null",
  "llm": "object | null",
  "budget": "object | null",
  "context": "object | null",
  "tags": ["string"],
  "sdk": {
    "name": "visibility",
    "version": "0.1.0"
  }
}
```

## 8.1 request object

```json
{
  "method": "GET | POST | PUT | PATCH | DELETE",
  "url": "/api/users",
  "route": "/api/users",
  "status_code": 200,
  "headers": {}
}
```

## 8.2 error object

```json
{
  "message": "Rate limit exceeded",
  "name": "RateLimitError",
  "stack": "optional stack trace",
  "code": "optional_error_code"
}
```

## 8.3 llm object

```json
{
  "provider": "openai",
  "model": "gpt-4o-mini",
  "prompt_tokens": 800,
  "completion_tokens": 200,
  "total_tokens": 1000,
  "estimated_cost_usd": 0.0004,
  "agent_id": "agent-001",
  "session_id": "session-123",
  "tool_name": "research_tool"
}
```

## 8.4 budget object

```json
{
  "monthly_limit_usd": 10.0,
  "used_usd": 8.4,
  "threshold": 0.8,
  "exceeded": false
}
```

## 8.5 Event type rules

Use these event types:

| type | meaning |
|---|---|
| request | API request |
| error | error or exception |
| llm | LLM call |
| metric | custom numeric metric |
| trace | agent step or trace event |
| budget | budget warning/exceeded event |
| custom | generic event |

---

# 9. Tool Contract for AI Agents

Visibility must expose three main tools:

1. `visibility_track`
2. `visibility_query`
3. `visibility_summary`

These tools must be exported as:

- OpenAI-compatible function schema
- MCP-style manifest

---

## 9.1 visibility_track

Purpose:

```txt
Record a new event.
```

Input:

```json
{
  "type": "request | error | llm | metric | trace | budget | custom",
  "name": "event name",
  "level": "debug | info | warn | error",
  "status": "success | failure",
  "duration_ms": 100,
  "request": {},
  "error": {},
  "llm": {},
  "context": {},
  "tags": []
}
```

Required:

```txt
type
name
```

Output:

```json
{
  "ok": true,
  "event": {}
}
```

---

## 9.2 visibility_query

Purpose:

```txt
Query stored events.
```

Input:

```json
{
  "type": "llm",
  "name": "openai.chat",
  "since": "2026-01-01T00:00:00Z",
  "until": "2026-12-31T23:59:59Z",
  "limit": 20
}
```

Output:

```json
{
  "ok": true,
  "events": []
}
```

---

## 9.3 visibility_summary

Purpose:

```txt
Generate a local usage summary.
```

Input:

```json
{
  "since": "optional ISO timestamp",
  "until": "optional ISO timestamp"
}
```

Output:

```json
{
  "ok": true,
  "summary": {
    "total_events": 0,
    "total_requests": 0,
    "total_errors": 0,
    "total_llm_calls": 0,
    "total_prompt_tokens": 0,
    "total_completion_tokens": 0,
    "total_tokens": 0,
    "estimated_cost_usd": 0.0,
    "top_models": [],
    "recent_errors": [],
    "budget": {}
  }
}
```

---

# 10. Module Responsibilities

## 10.1 src/visibility/__init__.py

Exports:

```python
Visibility
VisibilityConfig
execute_tool_call
get_openai_tool_schema
get_mcp_manifest
```

---

## 10.2 src/visibility/config.py

Responsibilities:

- store configuration
- provide defaults
- support budget limits
- support redaction keys
- support token cost rules
- support storage path

Configuration fields:

```python
service_name: str
environment: str
db_path: str
enabled: bool
sample_rate: float
redact_keys: list[str]
monthly_usd_limit: float | None
warning_threshold: float
token_cost_rules: list[dict]
```

Defaults:

```python
service_name = "visibility"
environment = "development"
db_path = ".visibility/visibility.db"
enabled = True
sample_rate = 1.0
redact_keys = [
    "authorization",
    "token",
    "api_key",
    "access_token",
    "refresh_token",
    "password",
    "secret"
]
monthly_usd_limit = None
warning_threshold = 0.8
```

---

## 10.3 src/visibility/events.py

Responsibilities:

- create event dictionary
- validate required fields
- generate UUID
- generate UTC timestamp
- attach SDK metadata
- ensure JSON serializability

---

## 10.4 src/visibility/redact.py

Responsibilities:

- recursively redact sensitive keys
- support nested dictionaries
- support lists
- replace secret values with `"[REDACTED]"`

Example:

```python
{
    "authorization": "Bearer token"
}
```

becomes:

```python
{
    "authorization": "[REDACTED]"
}
```

---

## 10.5 src/visibility/storage.py

Responsibilities:

- open SQLite database
- create table if not exists
- write event
- query events
- count events
- close database

SQLite table:

```sql
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    level TEXT NOT NULL,
    status TEXT,
    payload TEXT NOT NULL
);
```

Indexes:

```sql
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
CREATE INDEX IF NOT EXISTS idx_events_name ON events(name);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
```

Storage methods:

```python
write_event(event: dict) -> None
query(filters: dict) -> list[dict]
count(filters: dict) -> int
close() -> None
```

Query filters:

```python
type
name
since
until
limit
```

---

## 10.6 src/visibility/tracker.py

Main class:

```python
Visibility
```

Constructor:

```python
Visibility(
    service_name="my-app",
    environment="development",
    db_path=".visibility/visibility.db",
    monthly_usd_limit=None,
    warning_threshold=0.8,
    token_cost_rules=None
)
```

Methods:

```python
track_request(...)
track_error(...)
track_llm(...)
track_custom(...)
track_budget_warning(...)
track_budget_exceeded(...)
query(...)
summary(...)
close()
```

---

## 10.7 src/visibility/summary.py

Responsibilities:

- calculate totals
- calculate token usage
- calculate estimated cost
- find top models
- find recent errors
- calculate budget status

Summary output:

```json
{
  "total_events": 0,
  "total_requests": 0,
  "total_errors": 0,
  "total_llm_calls": 0,
  "total_prompt_tokens": 0,
  "total_completion_tokens": 0,
  "total_tokens": 0,
  "estimated_cost_usd": 0.0,
  "top_models": [],
  "recent_errors": [],
  "budget": {}
}
```

---

## 10.8 src/visibility/plugins.py

Responsibilities:

- allow plugins to receive events
- plugins must not crash core tracker
- plugin errors must be caught silently or logged internally

Plugin shape:

```python
class Plugin:
    name = "plugin-name"

    def on_event(self, event: dict, config: dict) -> None:
        pass
```

Built-in plugins:

1. ConsolePlugin
2. WebhookPlugin

ConsolePlugin:

- prints JSON event to stdout

WebhookPlugin:

- sends JSON event to HTTP endpoint
- uses Python standard library `urllib.request`
- must not require external `requests` package
- must not crash tracker if network fails

---

## 10.9 src/visibility/schemas.py

Responsibilities:

- generate OpenAI-compatible function schema
- generate MCP-style manifest
- include schemas for:
  - visibility_track
  - visibility_query
  - visibility_summary

Functions:

```python
get_openai_tool_schema() -> dict
get_mcp_manifest() -> dict
```

---

## 10.10 src/visibility/cli.py

Responsibilities:

- provide command-line interface
- output strict JSON only
- support schema, track, query, summary

Commands:

```bash
visibility schema
visibility track --json '{...}'
visibility query --type=llm --limit=20
visibility summary
```

Rules:

- stdout must be JSON
- errors must be JSON too
- no decorative text
- no stack traces unless debugging flag is used

Error output:

```json
{
  "ok": false,
  "error": "error message"
}
```

Success output:

```json
{
  "ok": true
}
```

---

# 11. Cost and Budget System

## 11.1 Token cost rules

Token cost rules should be simple dictionaries:

```python
[
    {
        "match_model": "gpt-4o-mini",
        "prompt_usd_per_1k": 0.00015,
        "completion_usd_per_1k": 0.0006
    },
    {
        "match_model": "gpt-4o",
        "prompt_usd_per_1k": 0.005,
        "completion_usd_per_1k": 0.015
    }
]
```

Cost formula:

```txt
estimated_cost_usd =
    prompt_tokens / 1000 * prompt_usd_per_1k
  + completion_tokens / 1000 * completion_usd_per_1k
```

## 11.2 Budget warning

If monthly usage crosses `warning_threshold`, create:

```json
{
  "type": "budget",
  "name": "budget.warning",
  "level": "warn"
}
```

Example:

```python
monthly_usd_limit = 10
warning_threshold = 0.8
```

Warning at:

```txt
8 USD
```

## 11.3 Budget exceeded

If monthly usage crosses `monthly_usd_limit`, create:

```json
{
  "type": "budget",
  "name": "budget.exceeded",
  "level": "error"
}
```

---

# 12. Redaction Rules

Redaction must happen before storage.

Default sensitive keys:

```txt
authorization
token
api_key
access_token
refresh_token
password
secret
```

Redaction must handle:

```python
{
    "headers": {
        "authorization": "Bearer abc"
    },
    "context": {
        "api_key": "sk-123"
    }
}
```

Result:

```python
{
    "headers": {
        "authorization": "[REDACTED]"
    },
    "context": {
        "api_key": "[REDACTED]"
    }
}
```

---

# 13. Testing Requirements

Tests must use pytest.

Tests must cover:

1. event creation
2. secret redaction
3. SQLite write/query
4. request tracking
5. error tracking
6. LLM tracking
7. token calculation
8. cost calculation
9. budget warning
10. budget exceeded
11. summary output
12. CLI schema output
13. tool-call execution

Tests must use temporary directories.

Do not write tests into the real `.visibility` folder.

---

# 14. Examples

## 14.1 examples/basic.py

Show:

- create tracker
- track request
- track error
- track LLM
- query events
- print summary

## 14.2 examples/agent_tool.py

Show:

- get tool schema
- simulate agent tool call
- execute tool call
- print result

---

# 15. Documentation Requirements

## README.md

README must include:

1. project title
2. one-line description
3. why Visibility exists
4. features
5. install command
6. quickstart code
7. CLI examples
8. agent integration example
9. roadmap
10. license

## docs/AGENT.md

AGENT.md must explain:

1. how AI agents should use Visibility
2. available tools
3. strict JSON output
4. example tool calls
5. example responses

---

# 16. Build Phases for Qwen Coder

Implement the project in these phases.

Do not skip phases.

Do not move to the next phase until the current phase is complete.

---

## Phase 1 — Specification and documentation

Create:

```txt
README.md
docs/AGENT.md
spec/event.schema.json
spec/tool.schema.json
```

Requirements:

- event schema must match this document
- tool schema must include visibility_track, visibility_query, visibility_summary
- README must be clear and professional
- AGENT.md must be written for AI agents

Stop after Phase 1 if response limit is reached.

---

## Phase 2 — Python package base

Create:

```txt
pyproject.toml
.gitignore
LICENSE
src/visibility/__init__.py
src/visibility/config.py
src/visibility/redact.py
src/visibility/events.py
src/visibility/storage.py
```

Requirements:

- Python 3.9 compatible
- no runtime dependencies
- SQLite storage works
- redaction works
- event builder works
- config supports budget and redaction

Stop after Phase 2 if response limit is reached.

---

## Phase 3 — Tracker, summary, and plugins

Create:

```txt
src/visibility/tracker.py
src/visibility/summary.py
src/visibility/plugins.py
```

Requirements:

- Visibility class works
- track_request works
- track_error works
- track_llm works
- track_custom works
- budget warning works
- budget exceeded works
- summary works
- plugins do not crash core tracker

Stop after Phase 3 if response limit is reached.

---

## Phase 4 — Agent schemas and CLI

Create:

```txt
src/visibility/schemas.py
src/visibility/cli.py
```

Requirements:

- OpenAI schema works
- MCP manifest works
- CLI schema command works
- CLI track command works
- CLI query command works
- CLI summary command works
- all CLI output is strict JSON

Stop after Phase 4 if response limit is reached.

---

## Phase 5 — Tests, examples, and CI

Create:

```txt
tests/test_events.py
tests/test_redact.py
tests/test_storage.py
tests/test_tracker.py
tests/test_summary.py
examples/basic.py
examples/agent_tool.py
.github/workflows/ci.yml
```

Requirements:

- pytest passes
- examples run without errors
- GitHub Actions runs tests
- no runtime dependencies added

Stop after Phase 5 when complete.

---

# 17. Public API Design

The package must expose:

```python
from visibility import (
    Visibility,
    VisibilityConfig,
    execute_tool_call,
    get_openai_tool_schema,
    get_mcp_manifest
)
```

Example:

```python
v = Visibility(service_name="demo")

v.track_request(
    name="api.users.list",
    method="GET",
    url="/api/users",
    status_code=200,
    duration_ms=42
)

v.track_llm(
    name="openai.chat",
    provider="openai",
    model="gpt-4o-mini",
    prompt_tokens=500,
    completion_tokens=100
)

events = v.query(type="llm", limit=10)

summary = v.summary()
```

---

# 18. Tool Call Executor

Create a helper function:

```python
execute_tool_call(payload: dict) -> dict
```

Expected input:

```json
{
  "tool": "visibility_track",
  "arguments": {
    "type": "llm",
    "name": "openai.chat",
    "llm": {
      "provider": "openai",
      "model": "gpt-4o-mini",
      "prompt_tokens": 500,
      "completion_tokens": 100
    }
  }
}
```

Expected output:

```json
{
  "ok": true,
  "event": {}
}
```

Supported tools:

```txt
visibility_track
visibility_query
visibility_summary
```

If tool is unknown:

```json
{
  "ok": false,
  "error": "Unknown tool"
}
```

---

# 19. Quality Rules

All code must be:

- clean
- commented where necessary
- modular
- testable
- predictable
- safe for local development
- safe for agent automation

Avoid:

- global state
- hidden prints
- blocking network calls
- complex class hierarchies
- unnecessary abstractions
- external dependencies
- decorative CLI output

---

# 20. Acceptance Criteria

Version 1 is complete only if all of these are true.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Tests

```bash
pytest
```

All tests pass.

## CLI schema

```bash
visibility schema
```

Returns JSON containing:

- OpenAI schema
- MCP manifest

## CLI track

```bash
visibility track --json '{"type":"custom","name":"demo.event"}'
```

Returns:

```json
{
  "ok": true
}
```

or equivalent success JSON.

## CLI query

```bash
visibility query --limit=10
```

Returns JSON events.

## CLI summary

```bash
visibility summary
```

Returns JSON summary.

## SDK example

This must work:

```python
from visibility import Visibility

v = Visibility(service_name="demo")

v.track_llm(
    name="openai.chat",
    provider="openai",
    model="gpt-4o-mini",
    prompt_tokens=500,
    completion_tokens=100
)

print(v.summary())
```

---

# 21. Final Instruction

Qwen Coder, now implement this project phase by phase.

Start with Phase 1.

After completing each phase, stop and wait for the user to say:

```txt
continue
```

Do not generate the entire repository in one response if it risks hitting output limits.

Prioritize correctness, modularity, and simplicity.
