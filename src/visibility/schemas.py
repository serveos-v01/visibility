"""
Schemas module for Visibility.

Generates OpenAI-compatible function schemas and MCP-style manifests
for agent integration.
"""

from typing import Dict, Any


def get_openai_tool_schema() -> Dict[str, Any]:
    """
    Generate OpenAI-compatible function schema for Visibility tools.
    
    Returns:
        Dictionary containing three function schemas:
        - visibility_track
        - visibility_query
        - visibility_summary
    """
    return {
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "visibility_track",
                    "description": "Record a new event in Visibility.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["request", "error", "llm", "metric", "trace", "budget", "custom"],
                                "description": "Type of event to record"
                            },
                            "name": {
                                "type": "string",
                                "description": "Stable event name"
                            },
                            "level": {
                                "type": "string",
                                "enum": ["debug", "info", "warn", "error"],
                                "description": "Log level"
                            },
                            "status": {
                                "type": "string",
                                "enum": ["success", "failure"],
                                "description": "Event status"
                            },
                            "duration_ms": {
                                "type": "number",
                                "description": "Duration in milliseconds"
                            },
                            "request": {
                                "type": "object",
                                "description": "Request object for request events"
                            },
                            "error": {
                                "type": "object",
                                "description": "Error object for error events"
                            },
                            "llm": {
                                "type": "object",
                                "description": "LLM object for LLM events"
                            },
                            "context": {
                                "type": "object",
                                "description": "Additional context"
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of tags"
                            }
                        },
                        "required": ["type", "name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "visibility_query",
                    "description": "Query stored events from Visibility.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "description": "Filter by event type"
                            },
                            "name": {
                                "type": "string",
                                "description": "Filter by event name"
                            },
                            "since": {
                                "type": "string",
                                "description": "Filter events after this ISO timestamp"
                            },
                            "until": {
                                "type": "string",
                                "description": "Filter events before this ISO timestamp"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of events to return"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "visibility_summary",
                    "description": "Generate a local usage summary from Visibility.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "since": {
                                "type": "string",
                                "description": "Filter events after this ISO timestamp"
                            },
                            "until": {
                                "type": "string",
                                "description": "Filter events before this ISO timestamp"
                            }
                        }
                    }
                }
            }
        ]
    }


def get_mcp_manifest() -> Dict[str, Any]:
    """
    Generate MCP-style manifest for Visibility.
    
    Returns:
        Dictionary containing MCP manifest with tools
    """
    return {
        "name": "visibility",
        "version": "0.1.0",
        "description": "Local-first observability, audit, and cost-guardrail SDK for AI agents",
        "tools": [
            {
                "name": "visibility_track",
                "description": "Record a new event in Visibility.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["request", "error", "llm", "metric", "trace", "budget", "custom"],
                            "description": "Type of event to record"
                        },
                        "name": {
                            "type": "string",
                            "description": "Stable event name"
                        },
                        "level": {
                            "type": "string",
                            "enum": ["debug", "info", "warn", "error"],
                            "description": "Log level"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["success", "failure"],
                            "description": "Event status"
                        },
                        "duration_ms": {
                            "type": "number",
                            "description": "Duration in milliseconds"
                        },
                        "request": {
                            "type": "object",
                            "description": "Request object for request events"
                        },
                        "error": {
                            "type": "object",
                            "description": "Error object for error events"
                        },
                        "llm": {
                            "type": "object",
                            "properties": {
                                "provider": {"type": "string"},
                                "model": {"type": "string"},
                                "prompt_tokens": {"type": "integer"},
                                "completion_tokens": {"type": "integer"},
                                "agent_id": {"type": "string"},
                                "session_id": {"type": "string"},
                                "tool_name": {"type": "string"}
                            },
                            "description": "LLM object for LLM events"
                        },
                        "context": {
                            "type": "object",
                            "description": "Additional context"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of tags"
                        }
                    },
                    "required": ["type", "name"]
                }
            },
            {
                "name": "visibility_query",
                "description": "Query stored events from Visibility.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "Filter by event type"
                        },
                        "name": {
                            "type": "string",
                            "description": "Filter by event name"
                        },
                        "since": {
                            "type": "string",
                            "description": "Filter events after this ISO timestamp"
                        },
                        "until": {
                            "type": "string",
                            "description": "Filter events before this ISO timestamp"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of events to return"
                        }
                    }
                }
            },
            {
                "name": "visibility_summary",
                "description": "Generate a local usage summary from Visibility.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "since": {
                            "type": "string",
                            "description": "Filter events after this ISO timestamp"
                        },
                        "until": {
                            "type": "string",
                            "description": "Filter events before this ISO timestamp"
                        }
                    }
                }
            }
        ]
    }
