"""Agent tool integration example for Visibility SDK."""

from visibility import execute_tool_call, get_openai_tool_schema, get_mcp_manifest

# Example 1: Get OpenAI tool schema
print("=== OpenAI Tool Schema ===")
schema = get_openai_tool_schema()
print(f"Available tools: {[t['function']['name'] for t in schema['tools']]}")

# Example 2: Get MCP manifest
print("\n=== MCP Manifest ===")
manifest = get_mcp_manifest()
print(f"Manifest name: {manifest['name']}")
print(f"Available tools: {[t['name'] for t in manifest['tools']]}")

# Example 3: Execute visibility_track tool call
print("\n=== Track LLM Event via Tool Call ===")
result = execute_tool_call({
    "tool": "visibility_track",
    "arguments": {
        "type": "llm",
        "name": "openai.chat",
        "llm": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "prompt_tokens": 500,
            "completion_tokens": 100,
            "agent_id": "agent-001",
            "session_id": "session-123"
        }
    }
})
print(f"Result: {result}")

# Example 4: Execute visibility_query tool call
print("\n=== Query Events via Tool Call ===")
result = execute_tool_call({
    "tool": "visibility_query",
    "arguments": {
        "type": "llm",
        "limit": 10
    }
})
print(f"Found {len(result.get('events', []))} events")

# Example 5: Execute visibility_summary tool call
print("\n=== Get Summary via Tool Call ===")
result = execute_tool_call({
    "tool": "visibility_summary",
    "arguments": {}
})
summary = result.get("summary", {})
print(f"Total LLM Calls: {summary.get('total_llm_calls', 0)}")
print(f"Total Tokens: {summary.get('total_tokens', 0)}")
print(f"Estimated Cost: ${summary.get('estimated_cost_usd', 0):.6f}")

# Example 6: Handle unknown tool
print("\n=== Unknown Tool Handling ===")
result = execute_tool_call({
    "tool": "unknown_tool",
    "arguments": {}
})
print(f"Result: {result}")

print("\nDone!")
