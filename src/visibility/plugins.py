"""
Plugins module for Visibility.

Allows plugins to receive events without crashing the core tracker.
Includes built-in ConsolePlugin and WebhookPlugin.
Also provides execute_tool_call for agent integration.
"""

import json
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod


class Plugin(ABC):
    """Base class for Visibility plugins."""
    
    name: str = "plugin"
    
    @abstractmethod
    def on_event(self, event: Dict[str, Any], config: Dict[str, Any]) -> None:
        """
        Called when an event is tracked.
        
        Args:
            event: The event dictionary
            config: Configuration dictionary
        """
        pass


class ConsolePlugin(Plugin):
    """Plugin that prints events as JSON to stdout."""
    
    name = "console"
    
    def on_event(self, event: Dict[str, Any], config: Dict[str, Any]) -> None:
        """Print event as JSON to stdout."""
        try:
            print(json.dumps(event, indent=2))
        except Exception:
            # Silently ignore errors to avoid crashing tracker
            pass


class WebhookPlugin(Plugin):
    """Plugin that sends events to an HTTP webhook endpoint."""
    
    name = "webhook"
    
    def __init__(self, webhook_url: str):
        """
        Initialize webhook plugin.
        
        Args:
            webhook_url: URL to send POST requests to
        """
        self.webhook_url = webhook_url
    
    def on_event(self, event: Dict[str, Any], config: Dict[str, Any]) -> None:
        """Send event to webhook URL."""
        try:
            # Use standard library urllib (no external dependencies)
            import urllib.request
            import urllib.error
            
            data = json.dumps(event).encode('utf-8')
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            
            # Send request with timeout
            urllib.request.urlopen(req, timeout=10)
        except Exception:
            # Silently ignore network errors to avoid crashing tracker
            pass


class PluginManager:
    """Manages plugins and dispatches events to them."""
    
    def __init__(self):
        """Initialize plugin manager."""
        self._plugins: list[Plugin] = []
    
    def register(self, plugin: Plugin) -> None:
        """
        Register a plugin.
        
        Args:
            plugin: Plugin instance to register
        """
        self._plugins.append(plugin)
    
    def dispatch(self, event: Dict[str, Any], config: Dict[str, Any]) -> None:
        """
        Dispatch event to all registered plugins.
        
        Args:
            event: Event dictionary
            config: Configuration dictionary
        """
        for plugin in self._plugins:
            try:
                plugin.on_event(event, config)
            except Exception:
                # Silently ignore plugin errors to avoid crashing tracker
                pass
    
    def clear(self) -> None:
        """Remove all registered plugins."""
        self._plugins.clear()


def execute_tool_call(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a tool call for AI agent integration.
    
    Args:
        payload: Tool call payload with 'tool' and 'arguments' fields
    
    Returns:
        Result dictionary with 'ok' field and either 'event'/'events'/'summary' or 'error'
    """
    from visibility import Visibility
    
    tool = payload.get("tool")
    arguments = payload.get("arguments", {})
    
    if tool == "visibility_track":
        try:
            v = Visibility()
            event_type = arguments.get("type", "custom")
            name = arguments.get("name", "unnamed")
            
            if event_type == "llm":
                llm_data = arguments.get("llm", {})
                event = v.track_llm(
                    name=name,
                    provider=llm_data.get("provider", "openai"),
                    model=llm_data.get("model", ""),
                    prompt_tokens=llm_data.get("prompt_tokens", 0),
                    completion_tokens=llm_data.get("completion_tokens", 0),
                    agent_id=llm_data.get("agent_id"),
                    session_id=llm_data.get("session_id"),
                    tool_name=llm_data.get("tool_name"),
                    duration_ms=arguments.get("duration_ms"),
                    context=arguments.get("context"),
                    tags=arguments.get("tags")
                )
            elif event_type == "request":
                request_data = arguments.get("request", {})
                event = v.track_request(
                    name=name,
                    method=request_data.get("method", "GET"),
                    url=request_data.get("url", ""),
                    status_code=request_data.get("status_code", 200),
                    duration_ms=arguments.get("duration_ms"),
                    context=arguments.get("context"),
                    tags=arguments.get("tags")
                )
            elif event_type == "error":
                error_data = arguments.get("error", {})
                event = v.track_error(
                    name=name,
                    message=error_data.get("message", "Unknown error"),
                    error_name=error_data.get("name", "Error"),
                    duration_ms=arguments.get("duration_ms"),
                    context=arguments.get("context"),
                    tags=arguments.get("tags")
                )
            else:
                event = v.track_custom(
                    name=name,
                    level=arguments.get("level", "info"),
                    status=arguments.get("status"),
                    duration_ms=arguments.get("duration_ms"),
                    context=arguments.get("context"),
                    tags=arguments.get("tags")
                )
            
            v.close()
            return {"ok": True, "event": event}
        
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    elif tool == "visibility_query":
        try:
            v = Visibility()
            events = v.query(
                event_type=arguments.get("type"),
                name=arguments.get("name"),
                since=arguments.get("since"),
                until=arguments.get("until"),
                limit=arguments.get("limit", 100)
            )
            v.close()
            return {"ok": True, "events": events}
        
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    elif tool == "visibility_summary":
        try:
            v = Visibility()
            summary = v.summary(
                since=arguments.get("since"),
                until=arguments.get("until")
            )
            v.close()
            return {"ok": True, "summary": summary}
        
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    else:
        return {"ok": False, "error": "Unknown tool"}
