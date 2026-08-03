"""
Tracker module for Visibility.

Main Visibility class that provides:
- Request tracking
- Error tracking
- LLM/token usage tracking
- Cost estimation
- Budget guardrails
- Event query API
- Summary report API
"""

from typing import Dict, Any, Optional, List

from visibility.config import VisibilityConfig
from visibility.events import create_event
from visibility.storage import Storage
from visibility.redact import redact_sensitive_data
from visibility.summary import calculate_summary
from visibility.plugins import PluginManager, ConsolePlugin


class Visibility:
    """Main tracker class for Visibility SDK."""
    
    def __init__(
        self,
        service_name: str = "visibility",
        environment: str = "development",
        db_path: str = ".visibility/visibility.db",
        monthly_usd_limit: Optional[float] = None,
        warning_threshold: float = 0.8,
        token_cost_rules: Optional[List[Dict]] = None,
        enable_console: bool = False,
    ):
        """
        Initialize Visibility tracker.
        
        Args:
            service_name: Name of the service/application
            environment: Environment name (development, staging, production)
            db_path: Path to SQLite database
            monthly_usd_limit: Optional monthly budget limit in USD
            warning_threshold: Threshold (0-1) for budget warnings
            token_cost_rules: List of token cost rules
            enable_console: If True, print events to console
        """
        self.service_name = service_name
        self.environment = environment
        self.db_path = db_path
        self.monthly_usd_limit = monthly_usd_limit
        self.warning_threshold = warning_threshold
        self.token_cost_rules = token_cost_rules or []
        
        # Initialize storage
        self._storage = Storage(db_path)
        
        # Initialize plugin manager
        self._plugin_manager = PluginManager()
        if enable_console:
            self._plugin_manager.register(ConsolePlugin())
        
        # Track budget state
        self._budget_warning_sent = False
        self._budget_exceeded_sent = False
    
    def _redact(self, data: Any) -> Any:
        """Redact sensitive data from dictionary."""
        config = VisibilityConfig()
        return redact_sensitive_data(data, config.redact_keys)
    
    def _check_budget(self, current_cost: float) -> Optional[Dict[str, Any]]:
        """
        Check budget status and return budget event if needed.
        
        Args:
            current_cost: Current total cost in USD
        
        Returns:
            Budget event dictionary or None
        """
        if self.monthly_usd_limit is None:
            return None
        
        threshold_amount = self.monthly_usd_limit * self.warning_threshold
        exceeded = current_cost >= self.monthly_usd_limit
        warning_needed = current_cost >= threshold_amount and not exceeded
        
        # Send warning event
        if warning_needed and not self._budget_warning_sent:
            self._budget_warning_sent = True
            return create_event(
                event_type="budget",
                name="budget.warning",
                level="warn",
                budget={
                    "monthly_limit_usd": self.monthly_usd_limit,
                    "used_usd": round(current_cost, 6),
                    "threshold": self.warning_threshold,
                    "exceeded": False
                }
            )
        
        # Send exceeded event
        if exceeded and not self._budget_exceeded_sent:
            self._budget_exceeded_sent = True
            return create_event(
                event_type="budget",
                name="budget.exceeded",
                level="error",
                budget={
                    "monthly_limit_usd": self.monthly_usd_limit,
                    "used_usd": round(current_cost, 6),
                    "threshold": self.warning_threshold,
                    "exceeded": True
                }
            )
        
        return None
    
    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """
        Calculate estimated cost for LLM call.
        
        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            model: Model name
        
        Returns:
            Estimated cost in USD
        """
        for rule in self.token_cost_rules:
            if rule.get("match_model") == model:
                prompt_cost = (prompt_tokens / 1000) * rule.get("prompt_usd_per_1k", 0)
                completion_cost = (completion_tokens / 1000) * rule.get("completion_usd_per_1k", 0)
                return prompt_cost + completion_cost
        return 0.0
    
    def track_request(
        self,
        name: str,
        method: str = "GET",
        url: str = "",
        route: str = "",
        status_code: int = 200,
        headers: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Track an API request.
        
        Args:
            name: Event name
            method: HTTP method
            url: Request URL
            route: Route pattern
            status_code: HTTP status code
            headers: Request/response headers
            duration_ms: Duration in milliseconds
            context: Additional context
            tags: List of tags
        
        Returns:
            Created event dictionary
        """
        request_obj = {
            "method": method,
            "url": url,
            "route": route,
            "status_code": status_code,
            "headers": self._redact(headers or {})
        }
        
        event = create_event(
            event_type="request",
            name=name,
            level="info",
            status="success" if 200 <= status_code < 400 else "failure",
            duration_ms=duration_ms,
            request=request_obj,
            context=self._redact(context or {}),
            tags=tags
        )
        
        self._storage.write_event(event)
        self._plugin_manager.dispatch(event, {"service_name": self.service_name})
        
        return event
    
    def track_error(
        self,
        name: str,
        message: str,
        error_name: str = "Error",
        stack: Optional[str] = None,
        code: Optional[str] = None,
        duration_ms: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Track an error.
        
        Args:
            name: Event name
            message: Error message
            error_name: Error class name
            stack: Stack trace
            code: Error code
            duration_ms: Duration in milliseconds
            context: Additional context
            tags: List of tags
        
        Returns:
            Created event dictionary
        """
        error_obj = {
            "message": message,
            "name": error_name,
            "stack": stack,
            "code": code
        }
        
        event = create_event(
            event_type="error",
            name=name,
            level="error",
            status="failure",
            duration_ms=duration_ms,
            error=error_obj,
            context=self._redact(context or {}),
            tags=tags
        )
        
        self._storage.write_event(event)
        self._plugin_manager.dispatch(event, {"service_name": self.service_name})
        
        return event
    
    def track_llm(
        self,
        name: str,
        provider: str = "openai",
        model: str = "",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        duration_ms: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Track an LLM call.
        
        Args:
            name: Event name
            provider: LLM provider (openai, anthropic, etc.)
            model: Model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            agent_id: Agent identifier
            session_id: Session identifier
            tool_name: Tool name if called by a tool
            duration_ms: Duration in milliseconds
            context: Additional context
            tags: List of tags
        
        Returns:
            Created event dictionary
        """
        total_tokens = prompt_tokens + completion_tokens
        estimated_cost = self._calculate_cost(prompt_tokens, completion_tokens, model)
        
        llm_obj = {
            "provider": provider,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": round(estimated_cost, 6),
            "agent_id": agent_id,
            "session_id": session_id,
            "tool_name": tool_name
        }
        
        event = create_event(
            event_type="llm",
            name=name,
            level="info",
            status="success",
            duration_ms=duration_ms,
            llm=llm_obj,
            context=self._redact(context or {}),
            tags=tags
        )
        
        self._storage.write_event(event)
        self._plugin_manager.dispatch(event, {"service_name": self.service_name})
        
        # Check budget after LLM call
        summary = self.summary()
        budget_event = self._check_budget(summary["estimated_cost_usd"])
        if budget_event:
            self._storage.write_event(budget_event)
            self._plugin_manager.dispatch(budget_event, {"service_name": self.service_name})
        
        return event
    
    def track_custom(
        self,
        name: str,
        level: str = "info",
        status: Optional[str] = None,
        duration_ms: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Track a custom event.
        
        Args:
            name: Event name
            level: Log level
            status: Event status
            duration_ms: Duration in milliseconds
            context: Additional context
            tags: List of tags
        
        Returns:
            Created event dictionary
        """
        event = create_event(
            event_type="custom",
            name=name,
            level=level,
            status=status,
            duration_ms=duration_ms,
            context=self._redact(context or {}),
            tags=tags
        )
        
        self._storage.write_event(event)
        self._plugin_manager.dispatch(event, {"service_name": self.service_name})
        
        return event
    
    def track_budget_warning(self) -> Dict[str, Any]:
        """Track a manual budget warning event."""
        event = create_event(
            event_type="budget",
            name="budget.warning",
            level="warn",
            budget={
                "monthly_limit_usd": self.monthly_usd_limit,
                "used_usd": 0,
                "threshold": self.warning_threshold,
                "exceeded": False
            }
        )
        
        self._storage.write_event(event)
        self._plugin_manager.dispatch(event, {"service_name": self.service_name})
        
        return event
    
    def track_budget_exceeded(self) -> Dict[str, Any]:
        """Track a manual budget exceeded event."""
        event = create_event(
            event_type="budget",
            name="budget.exceeded",
            level="error",
            budget={
                "monthly_limit_usd": self.monthly_usd_limit,
                "used_usd": 0,
                "threshold": self.warning_threshold,
                "exceeded": True
            }
        )
        
        self._storage.write_event(event)
        self._plugin_manager.dispatch(event, {"service_name": self.service_name})
        
        return event
    
    def query(
        self,
        event_type: Optional[str] = None,
        name: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: Optional[int] = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query events from storage.
        
        Args:
            event_type: Filter by event type
            name: Filter by event name
            since: Filter events after this ISO timestamp
            until: Filter events before this ISO timestamp
            limit: Maximum number of events to return
        
        Returns:
            List of event dictionaries
        """
        return self._storage.query(
            event_type=event_type,
            name=name,
            since=since,
            until=until,
            limit=limit
        )
    
    def summary(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a summary report.
        
        Args:
            since: Filter events after this ISO timestamp
            until: Filter events before this ISO timestamp
        
        Returns:
            Summary dictionary
        """
        events = self._storage.query(since=since, until=until)
        return calculate_summary(events, self.monthly_usd_limit)
    
    def close(self) -> None:
        """Close storage connection."""
        self._storage.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
