# Agent Harness Safety Layer

## Overview

The **Agent Harness** is a self-regulating safety layer that wraps around AI agent actions to ensure safety, budget compliance, and error recovery. It acts as both a **Gatekeeper** (pre-flight checks) and an **Evaluator** (post-flight evaluation) for every action your agent takes.

## How the Harness Protects Your Agent

### 1. Budget Guardrails
- **Prevents Overspending**: Before any action executes, the harness checks if the estimated cost would exceed your configured budget limit
- **Automatic Halting**: When budget is exceeded, all further actions are immediately blocked
- **Warning Threshold**: Get notified when spending reaches 80% (configurable) of your budget

### 2. Circuit Breaker Pattern
- **Error Rate Monitoring**: Tracks success/failure rates across all agent actions
- **Automatic Halt**: When error rate exceeds threshold (default 50%), the harness enters HALTED state
- **Prevents Cascading Failures**: Stops the agent from continuing when things are going wrong

### 3. Token Limits
- **Per-Action Token Guard**: Blocks actions that would exceed maximum token limits
- **Prevents Resource Exhaustion**: Protects against runaway token consumption

### 4. Self-Correction Prompts
- **Intelligent Error Analysis**: On failure, generates context-aware correction suggestions
- **Retry Guidance**: Provides specific hints based on error type (budget, tokens, rate limits, timeouts)
- **JSON Output**: All correction prompts are valid JSON for easy agent parsing

### 5. State Management
- **Three States**: `READY` → `WARNING` → `HALTED`
- **Automatic Transitions**: State changes automatically based on metrics
- **Manual Reset**: Can reset metrics and status for new sessions

## Quick Start

```python
from visibility import AgentHarness, HarnessConfig

# Initialize with budget and error rate limits
harness = AgentHarness(
    config=HarnessConfig(
        budget_limit_usd=10.0,      # Max $10 per session
        max_error_rate=0.3,         # Halt if >30% errors
        max_tokens=50000,           # Max 50k tokens per action
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
    
    if not eval_result["success"]:
        # Get self-correction prompt
        correction = eval_result["corrective_prompt"]
        print(f"Retry hint: {correction}")
else:
    print(f"Action blocked: {check['reason']}")
```

## Using the Decorator

For automatic wrapping of functions:

```python
from visibility import AgentHarness, HarnessConfig, with_harness

harness = AgentHarness(config=HarnessConfig(budget_limit_usd=5.0))

@with_harness(harness, action_name="agent.search")
def search_knowledge_base(query: str):
    return {"results": [...], "status": "success"}

result = search_knowledge_base("What is X?")
# Harness automatically handles pre/post checks
```

## API Reference

### HarnessConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `budget_limit_usd` | `float` | `None` | Maximum budget in USD |
| `max_tokens` | `int` | `100000` | Max tokens per action |
| `max_error_rate` | `float` | `0.5` | Error rate threshold (0-1) |
| `timeout_ms` | `int` | `30000` | Max execution time |
| `warning_budget_threshold` | `float` | `0.8` | Budget warning threshold |
| `max_actions_per_session` | `int` | `1000` | Max actions per session |

### AgentHarness Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `pre_flight_check()` | Validate before execution | `{allowed: bool, reason: str, status: str, metrics: dict}` |
| `post_flight_eval()` | Evaluate after execution | `{success: bool, status: str, metrics: dict, corrective_prompt: str}` |
| `get_self_correction_prompt()` | Generate retry guidance | JSON string with correction hints |
| `check()` | Simple API for pre-flight | Same as `pre_flight_check()` |
| `evaluate()` | Simple API for post-flight | Same as `post_flight_eval()` |
| `reset_metrics()` | Clear all metrics | `{reset: bool, status: str}` |
| `get_status_report()` | Get comprehensive report | Full status and metrics dict |

### HarnessStatus Enum

- `READY`: All systems operational
- `WARNING`: Approaching limits (e.g., 80% budget used)
- `HALTED`: Action blocked due to limit exceeded

## Integration with Visibility Tracker

The harness works seamlessly with the Visibility tracker:

```python
from visibility import Visibility, AgentHarness, HarnessConfig

tracker = Visibility(
    service_name="my-agent",
    monthly_usd_limit=20.0,
)

harness = AgentHarness(
    config=HarnessConfig(budget_limit_usd=20.0),
    service_name="my-agent",
)

# Use both together
check = harness.check(action_name="llm.call", estimated_cost_usd=0.10)

if check["allowed"]:
    event = tracker.track_llm(
        name="llm.completion",
        model="gpt-4o-mini",
        prompt_tokens=500,
        completion_tokens=200,
    )
    
    harness.evaluate(
        result={"status": "success"},
        cost_usd=event["llm"]["estimated_cost_usd"],
    )
```

## Best Practices

1. **Set Conservative Limits**: Start with lower budgets and error thresholds
2. **Monitor Status**: Regularly check `harness.status` and `harness.get_status_report()`
3. **Use Self-Correction**: Implement retry logic using the corrective prompts
4. **Reset Between Sessions**: Call `reset_metrics()` when starting new user sessions
5. **Log Decisions**: The harness uses Python logging for all decisions (no print statements)

## Zero Dependencies

The harness uses only Python standard library modules:
- `json` for serialization
- `logging` for structured logging
- `dataclasses` for configuration
- `enum` for status types
- `time` for metrics tracking

No external packages required.
