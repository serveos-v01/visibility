"""Basic usage example for Visibility SDK."""

from visibility import Visibility

# Create tracker instance
v = Visibility(service_name="my-agent")

# Track an LLM call
v.track_llm(
    name="openai.chat",
    provider="openai",
    model="gpt-4o-mini",
    prompt_tokens=800,
    completion_tokens=200
)

# Track an API request
v.track_request(
    name="api.users.list",
    method="GET",
    url="/api/users",
    status_code=200,
    duration_ms=42
)

# Track an error
v.track_error(
    name="api.error",
    message="Rate limit exceeded",
    error_name="RateLimitError"
)

# Track a custom event
v.track_custom(
    name="user.action",
    level="info",
    tags=["action", "user"]
)

# Query events
print("=== Recent LLM Events ===")
llm_events = v.query(event_type="llm", limit=5)
for event in llm_events:
    print(f"  - {event['name']}: {event['llm']['model']} ({event['llm']['total_tokens']} tokens)")

# Generate summary
print("\n=== Summary ===")
summary = v.summary()
print(f"Total Events: {summary['total_events']}")
print(f"Total LLM Calls: {summary['total_llm_calls']}")
print(f"Total Tokens: {summary['total_tokens']}")
print(f"Estimated Cost: ${summary['estimated_cost_usd']:.6f}")
print(f"Top Models: {[m['model'] for m in summary['top_models']]}")

# Close the tracker
v.close()

print("\nDone!")
