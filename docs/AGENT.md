# Visibility for AI Agents

This document explains how AI agents should integrate with Visibility.

## Overview

Visibility is designed to be **machine-readable first, human-readable second**. This makes it ideal for AI agent integration.

## Available Tools

Visibility exposes three tools that agents can call:

### 1. visibility_track

**Purpose:** Record a new event to the visibility tracker.

**Input Schema:**
```json
{
  "type": "request | error | llm | metric | trace | budget | custom",
  "name": "string (required)",
  "level": "debug | info | warn | error",
  "status": "success | failure",
  "duration_ms": "number",
  "request": "object",
  "error": "object",
  "llm": "object",
  "context": "object",
  "tags": ["string"]
}
```

**Required Fields:**
- `type` - The event type
- `name` - Stable event identifier

**Output:**
```json
{
  "ok": true,
  "event": { /* full event object */ }
}
```

**Example Usage:**
```python
from visibility import execute_tool_call

# Track an LLM call
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

# Track a request
result = execute_tool_call({
    "tool": "visibility_track",
    "arguments": {
        "type": "request",
        "name": "api.users.list",
        "request": {
            "method": "GET",
            "url": "/api/users",
            "status_code": 200
        },
        "duration_ms": 42
    }
})

# Track an error
result = execute_tool_call({
    "tool": "visibility_track",
    "arguments": {
        "type": "error",
        "name": "api.error",
        "error": {
            "message": "Rate limit exceeded",
            "name": "RateLimitError"
        },
        "level": "error"
    }
})
```

---

### 2. visibility_query

**Purpose:** Query stored events with filters.

**Input Schema:**
```json
{
  "type": "string (optional)",
  "name": "string (optional)",
  "since": "ISO 8601 timestamp (optional)",
  "until": "ISO 8601 timestamp (optional)",
  "limit": "number (optional, default 20)"
}
```

**Output:**
```json
{
  "ok": true,
  "events": [ /* array of event objects */ ]
}
```

**Example Usage:**
```python
from visibility import execute_tool_call

# Query recent LLM calls
result = execute_tool_call({
    "tool": "visibility_query",
    "arguments": {
        "type": "llm",
        "limit": 10
    }
})

# Query errors
result = execute_tool_call({
    "tool": "visibility_query",
    "arguments": {
        "type": "error",
        "limit": 5
    }
})

# Query by name
result = execute_tool_call({
    "tool": "visibility_query",
    "arguments": {
        "name": "openai.chat",
        "limit": 20
    }
})
```

---

### 3. visibility_summary

**Purpose:** Generate a usage summary report.

**Input Schema:**
```json
{
  "since": "ISO 8601 timestamp (optional)",
  "until": "ISO 8601 timestamp (optional)"
}
```

**Output:**
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

**Example Usage:**
```python
from visibility import execute_tool_call

# Get full summary
result = execute_tool_call({
    "tool": "visibility_summary",
    "arguments": {}
})

# Get summary for specific time range
result = execute_tool_call({
    "tool": "visibility_summary",
    "arguments": {
        "since": "2026-01-01T00:00:00Z"
    }
})
```

---

## Strict JSON Output

All Visibility outputs are strict JSON. This means:

1. **No decorative text** - Only JSON objects
2. **Consistent structure** - Always `{ "ok": boolean, ... }`
3. **Machine-parseable** - Easy to parse in any language
4. **Predictable fields** - Same fields every time

### Success Response Pattern
```json
{
  "ok": true,
  "data": { ... }
}
```

### Error Response Pattern
```json
{
  "ok": false,
  "error": "error message"
}
```

---

## Complete Agent Workflow Example

Here's how an autonomous agent might use Visibility:

```python
from visibility import execute_tool_call, get_openai_tool_schema

# Step 1: Get tool schemas for function calling
schemas = get_openai_tool_schema()

# Step 2: During operation, track actions
# Agent makes an API call
execute_tool_call({
    "tool": "visibility_track",
    "arguments": {
        "type": "request",
        "name": "external.api.call",
        "request": {
            "method": "POST",
            "url": "https://api.example.com/data",
            "status_code": 200
        },
        "duration_ms": 150,
        "status": "success"
    }
})

# Agent uses an LLM
execute_tool_call({
    "tool": "visibility_track",
    "arguments": {
        "type": "llm",
        "name": "openai.chat",
        "llm": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "prompt_tokens": 500,
            "completion_tokens": 150
        }
    }
})

# An error occurs
execute_tool_call({
    "tool": "visibility_track",
    "arguments": {
        "type": "error",
        "name": "agent.step.failed",
        "error": {
            "message": "Failed to parse response",
            "name": "ParseError"
        },
        "level": "error"
    }
})

# Step 3: Periodically check status
summary_result = execute_tool_call({
    "tool": "visibility_summary",
    "arguments": {}
})

print(f"Total LLM calls: {summary_result['summary']['total_llm_calls']}")
print(f"Estimated cost: ${summary_result['summary']['estimated_cost_usd']:.4f}")

# Step 4: Query recent activity if needed
recent_llm = execute_tool_call({
    "tool": "visibility_query",
    "arguments": {
        "type": "llm",
        "limit": 5
    }
})

for event in recent_llm['events']:
    print(f"Model: {event['llm']['model']}, Tokens: {event['llm']['total_tokens']}")
```

---

## Event Types Reference

| Type | When to Use | Key Fields |
|------|-------------|------------|
| `request` | API/HTTP requests | `request`, `duration_ms`, `status` |
| `error` | Errors/exceptions | `error`, `level="error"` |
| `llm` | LLM calls | `llm` (provider, model, tokens) |
| `metric` | Custom metrics | `context` with numeric values |
| `trace` | Agent steps/traces | `context`, `tags` |
| `budget` | Budget alerts | `budget` (limit, used, exceeded) |
| `custom` | Generic events | Any relevant fields |

---

## Best Practices for Agents

1. **Track all external calls** - APIs, databases, file operations
2. **Track all LLM usage** - Include provider, model, and token counts
3. **Track errors immediately** - Use `level="error"` for failures
4. **Use meaningful names** - Event names should be stable and descriptive
5. **Add context** - Include relevant metadata in `context` field
6. **Tag related events** - Use `tags` to group related activities
7. **Check budget periodically** - Use `visibility_summary` to monitor costs
8. **Query when debugging** - Use `visibility_query` to inspect past events

---

## CLI Usage for Agents

Agents can also use the CLI directly:

```bash
# Track via CLI
visibility track --json '{"type":"custom","name":"agent.action","context":{"action":"research"}}'

# Query via CLI
visibility query --type=llm --limit=10

# Summary via CLI
visibility summary
```

All CLI output is strict JSON, making it easy to parse in scripts.

---

## Getting Tool Schemas Programmatically

```python
from visibility import get_openai_tool_schema, get_mcp_manifest

# Get OpenAI-compatible function schemas
openai_schema = get_openai_tool_schema()

# Get MCP-style manifest
mcp_manifest = get_mcp_manifest()
```

These schemas can be used to configure function calling in AI frameworks.
