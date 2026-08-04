# Visibility 👁️

A local-first, agent-ready observability SDK for AI agents and LLM applications with built-in safety harness.

## Features

- **Request Tracking** - Track API requests with method, URL, status codes
- **Error Tracking** - Capture errors with stack traces
- **LLM Call Tracking** - Monitor token usage and estimated costs
- **Budget Guardrails** - Set monthly limits and receive warnings
- **Agent Harness Safety Layer** - Self-regulating safety wrapper with circuit breaker
- **Secret Redaction** - Automatically redact sensitive keys
- **Event Query API** - Query stored events with filters
- **Summary Reports** - Generate usage summaries
- **CLI Tool** - Full CLI with schema, track, query, and summary commands
- **Agent Integration** - OpenAI-compatible tool schemas

## Installation

```bash
pip install visibility
```

Or from source:

```bash
git clone https://github.com/serveos-v01/visibility.git
cd visibility
pip install -e ".[dev]"
```

## Quickstart

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

v.track_request(
    name="api.users.list",
    method="GET",
    url="/api/users",
    status_code=200,
    duration_ms=42
)

print(v.summary())
```

## CLI Usage

```bash
# View tool schemas
visibility schema

# Track an event
visibility track --json '{"type":"custom","name":"demo.event"}'

# Query events
visibility query --type=llm --limit=20

# Get summary
visibility summary
```

All CLI output is strict JSON.

## Agent Integration

Visibility exposes three tools for AI agents:

1. **visibility_track** - Record events
2. **visibility_query** - Query stored events
3. **visibility_summary** - Generate usage summaries

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

See [docs/AGENT.md](docs/AGENT.md) for details.

## Agent Harness Safety Layer

The **Agent Harness** is a self-regulating safety layer that wraps around AI agent actions to ensure safety, budget compliance, and error recovery. It acts as both a **Gatekeeper** (pre-flight checks) and an **Evaluator** (post-flight evaluation).

### Key Features

- **Budget Guardrails**: Blocks actions that would exceed your budget limit
- **Circuit Breaker**: Automatically halts when error rate exceeds threshold
- **Token Limits**: Prevents runaway token consumption
- **Self-Correction Prompts**: Generates intelligent retry guidance on failures
- **State Management**: Three states (`READY` → `WARNING` → `HALTED`) with automatic transitions

### Quick Example

```python
from visibility import AgentHarness, HarnessConfig

# Initialize harness with limits
harness = AgentHarness(
    config=HarnessConfig(
        budget_limit_usd=10.0,   # Max $10 per session
        max_error_rate=0.3,      # Halt if >30% errors
        max_tokens=50000,        # Max 50k tokens per action
    ),
    service_name="my-agent",
)

# Pre-flight check before executing action
check = harness.pre_flight_check(
    action_name="llm.completion",
    estimated_cost_usd=0.05,
    estimated_tokens=1000,
)

if check["allowed"]:
    # Execute your agent action
    result = call_your_llm()
    
    # Post-flight evaluation
    eval_result = harness.post_flight_eval(
        result=result,
        duration_ms=1500,
        tokens_used=950,
        cost_usd=0.04,
    )
else:
    print(f"Action blocked: {check['reason']}")
```

### Using the Decorator

```python
from visibility import AgentHarness, HarnessConfig, with_harness

harness = AgentHarness(config=HarnessConfig(budget_limit_usd=5.0))

@with_harness(harness, action_name="agent.search")
def search_knowledge_base(query: str):
    return {"results": [...], "status": "success"}

result = search_knowledge_base("What is X?")
# Harness automatically handles pre/post checks
```

See [docs/harness.md](docs/harness.md) for complete documentation.

## Event Types

| Type | Description |
|------|-------------|
| `request` | API request tracking |
| `error` | Error capture |
| `llm` | LLM call with token usage |
| `metric` | Custom numeric metrics |
| `trace` | Agent steps or trace events |
| `budget` | Budget warnings/exceeded |
| `custom` | Generic custom events |

## Secret Redaction

Visibility automatically redacts sensitive keys:

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

Default redacted keys: `authorization`, `token`, `api_key`, `access_token`, `refresh_token`, `password`, `secret`

## Cost Tracking

Built-in cost estimation for LLM calls:

```python
v = Visibility(
    service_name="my-app",
    monthly_usd_limit=10.0,
    warning_threshold=0.8
)
```

## Project Structure

```
visibility/
├─ src/visibility/       # Core SDK
│  ├─ tracker.py         # Event tracking and storage
│  ├─ harness.py         # Agent safety layer (NEW)
│  ├─ config.py          # Configuration classes
│  ├─ schemas.py         # Tool schemas for agents
│  └─ ...
├─ tests/                # Test suite (77 passing tests)
├─ examples/             # Usage examples
│  ├─ basic.py           # Basic tracking examples
│  └─ harness_usage.py   # Harness safety layer examples (NEW)
├─ spec/                 # JSON schemas
├─ docs/                 # Documentation
│  ├─ AGENT.md           # Agent integration guide
│  └─ harness.md         # Harness safety layer docs (NEW)
└─ .github/workflows/    # CI/CD
```

## License

MIT License - see [LICENSE](LICENSE) for details.
