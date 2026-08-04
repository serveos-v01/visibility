"""
Visibility — A local-first, agent-ready observability SDK for AI agents and LLM applications.
"""

from visibility.config import VisibilityConfig
from visibility.tracker import Visibility
from visibility.schemas import get_openai_tool_schema, get_mcp_manifest
from visibility.plugins import execute_tool_call
from visibility.harness import (
    AgentHarness,
    HarnessConfig,
    HarnessStatus,
    HarnessMetrics,
    with_harness,
)

__version__ = "0.1.0"
__all__ = [
    "Visibility",
    "VisibilityConfig",
    "execute_tool_call",
    "get_openai_tool_schema",
    "get_mcp_manifest",
    "AgentHarness",
    "HarnessConfig",
    "HarnessStatus",
    "HarnessMetrics",
    "with_harness",
]
