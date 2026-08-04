"""
Harness module for Visibility.

Provides a self-regulating safety layer that wraps around AI agent actions
to ensure safety, budget compliance, and error recovery.

The Harness acts as a "Gatekeeper" (Pre-flight) and an "Evaluator" (Post-flight)
for every action the agent takes.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List, Callable


# Configure logging (no print statements)
logger = logging.getLogger(__name__)


class HarnessStatus(Enum):
    """Enum representing the current state of the harness."""
    READY = "READY"
    WARNING = "WARNING"
    HALTED = "HALTED"


@dataclass
class HarnessConfig:
    """
    Configuration dataclass to store limits for the harness.
    
    Attributes:
        budget_limit_usd: Maximum budget in USD before halting
        max_tokens: Maximum tokens allowed per action
        max_error_rate: Threshold (0-1) for error rate before circuit breaker triggers
        timeout_ms: Maximum execution time in milliseconds for an action
        warning_budget_threshold: Threshold (0-1) for budget warnings
        max_actions_per_session: Maximum number of actions allowed per session
    """
    budget_limit_usd: Optional[float] = None
    max_tokens: int = 100000
    max_error_rate: float = 0.5
    timeout_ms: int = 30000
    warning_budget_threshold: float = 0.8
    max_actions_per_session: int = 1000


@dataclass
class HarnessMetrics:
    """
    Dataclass to track metrics for the harness.
    
    Attributes:
        total_actions: Total number of actions attempted
        successful_actions: Number of successful actions
        failed_actions: Number of failed actions
        total_spend_usd: Total spend in USD
        total_tokens_used: Total tokens consumed
        errors: List of recent error messages
        start_time: Timestamp when harness started tracking
    """
    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    total_spend_usd: float = 0.0
    total_tokens_used: int = 0
    errors: List[str] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    
    @property
    def error_rate(self) -> float:
        """Calculate current error rate."""
        if self.total_actions == 0:
            return 0.0
        return self.failed_actions / self.total_actions
    
    @property
    def success_rate(self) -> float:
        """Calculate current success rate."""
        if self.total_actions == 0:
            return 1.0
        return self.successful_actions / self.total_actions


class AgentHarness:
    """
    Main controller for the Agent Harness safety layer.
    
    This class provides pre-flight checks and post-flight evaluation
    for AI agent actions, ensuring safety, budget compliance, and
    automatic error recovery through self-correction prompts.
    
    Usage:
        >>> harness = AgentHarness(budget_limit_usd=10.0, max_error_rate=0.3)
        >>> 
        >>> # Pre-flight check
        >>> check_result = harness.pre_flight_check(action_name="llm.completion")
        >>> if check_result["allowed"]:
        ...     # Execute action
        ...     result = execute_action()
        ...     # Post-flight evaluation
        ...     eval_result = harness.post_flight_eval(result, duration_ms=1500)
        >>> 
        >>> # Get self-correction prompt on failure
        >>> correction = harness.get_self_correction_prompt()
    """
    
    def __init__(
        self,
        config: Optional[HarnessConfig] = None,
        service_name: str = "visibility",
        environment: str = "development",
    ):
        """
        Initialize the Agent Harness.
        
        Args:
            config: HarnessConfig instance with limits
            service_name: Name of the service/application
            environment: Environment name (development, staging, production)
        """
        self.config = config or HarnessConfig()
        self.service_name = service_name
        self.environment = environment
        self._metrics = HarnessMetrics()
        self._status = HarnessStatus.READY
        self._last_error: Optional[str] = None
        self._budget_warning_sent = False
        
        logger.info(
            f"AgentHarness initialized for {service_name} ({environment}) "
            f"with budget_limit={self.config.budget_limit_usd}, "
            f"max_error_rate={self.config.max_error_rate}"
        )
    
    @property
    def status(self) -> HarnessStatus:
        """Get current harness status."""
        return self._status
    
    @property
    def metrics(self) -> HarnessMetrics:
        """Get current harness metrics."""
        return self._metrics
    
    def _update_status(self) -> None:
        """Update harness status based on current metrics and config."""
        # Check if halted due to error rate
        if self._metrics.error_rate >= self.config.max_error_rate:
            self._status = HarnessStatus.HALTED
            logger.warning(
                f"Harness HALTED: error rate {self._metrics.error_rate:.2%} "
                f"exceeds threshold {self.config.max_error_rate:.2%}"
            )
            return
        
        # Check if halted due to budget
        if self.config.budget_limit_usd is not None:
            if self._metrics.total_spend_usd >= self.config.budget_limit_usd:
                self._status = HarnessStatus.HALTED
                logger.warning(
                    f"Harness HALTED: budget ${self._metrics.total_spend_usd:.4f} "
                    f"exceeds limit ${self.config.budget_limit_usd:.2f}"
                )
                return
            
            # Check for warning state
            threshold_amount = self.config.budget_limit_usd * self.config.warning_budget_threshold
            if self._metrics.total_spend_usd >= threshold_amount:
                if self._status != HarnessStatus.WARNING:
                    self._status = HarnessStatus.WARNING
                    logger.info(
                        f"Harness WARNING: budget ${self._metrics.total_spend_usd:.4f} "
                        f"exceeds {self.config.warning_budget_threshold:.0%} threshold"
                    )
                return
        
        # Default to READY if no issues
        if self._status != HarnessStatus.READY:
            self._status = HarnessStatus.READY
            logger.info("Harness status changed to READY")
    
    def pre_flight_check(
        self,
        action_name: str = "",
        estimated_tokens: int = 0,
        estimated_cost_usd: float = 0.0,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Validate budget/time BEFORE execution.
        
        This is the "Gatekeeper" function that checks if an action
        should be allowed to proceed based on current limits.
        
        Args:
            action_name: Name of the action to be executed
            estimated_tokens: Estimated tokens for this action
            estimated_cost_usd: Estimated cost for this action
            context: Additional context about the action
        
        Returns:
            Dictionary with keys:
                - allowed: bool indicating if action can proceed
                - reason: str explaining the decision
                - status: current harness status
                - metrics: current metrics snapshot
        """
        # Build response structure
        response = {
            "allowed": True,
            "reason": "",
            "status": self._status.value,
            "metrics": {
                "total_actions": self._metrics.total_actions,
                "error_rate": round(self._metrics.error_rate, 4),
                "total_spend_usd": round(self._metrics.total_spend_usd, 6),
                "total_tokens_used": self._metrics.total_tokens_used,
            }
        }
        
        # Check if harness is halted
        if self._status == HarnessStatus.HALTED:
            response["allowed"] = False
            response["reason"] = f"Harness is in HALTED state. Error rate: {self._metrics.error_rate:.2%}"
            if self.config.budget_limit_usd is not None:
                response["reason"] += f", Budget used: ${self._metrics.total_spend_usd:.4f}/${self.config.budget_limit_usd:.2f}"
            return response
        
        # Budget guard: Check if adding this action would exceed budget
        if self.config.budget_limit_usd is not None:
            projected_spend = self._metrics.total_spend_usd + estimated_cost_usd
            if projected_spend >= self.config.budget_limit_usd:
                response["allowed"] = False
                response["reason"] = (
                    f"Budget guard triggered. Projected spend ${projected_spend:.4f} "
                    f"would exceed limit ${self.config.budget_limit_usd:.2f}"
                )
                return response
        
        # Token guard: Check if estimated tokens exceed limit
        if estimated_tokens > self.config.max_tokens:
            response["allowed"] = False
            response["reason"] = (
                f"Token guard triggered. Estimated tokens {estimated_tokens} "
                f"exceeds limit {self.config.max_tokens}"
            )
            return response
        
        # Error rate guard: Check current error rate
        if self._metrics.error_rate >= self.config.max_error_rate:
            response["allowed"] = False
            response["reason"] = (
                f"Error rate guard triggered. Current error rate {self._metrics.error_rate:.2%} "
                f"exceeds threshold {self.config.max_error_rate:.2%}"
            )
            return response
        
        # Max actions guard
        if self._metrics.total_actions >= self.config.max_actions_per_session:
            response["allowed"] = False
            response["reason"] = (
                f"Action limit reached. Total actions {self._metrics.total_actions} "
                f"equals limit {self.config.max_actions_per_session}"
            )
            return response
        
        response["reason"] = "Pre-flight check passed. Action allowed."
        logger.debug(f"Pre-flight check passed for action: {action_name}")
        
        return response
    
    def post_flight_eval(
        self,
        result: Any,
        duration_ms: float,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
        action_name: str = "",
    ) -> Dict[str, Any]:
        """
        Evaluate success/failure AFTER execution. Updates metrics.
        
        This is the "Evaluator" function that records the outcome
        of an action and updates internal metrics.
        
        Args:
            result: The result of the action (can be dict, object, or exception)
            duration_ms: Duration of the action in milliseconds
            tokens_used: Actual tokens consumed
            cost_usd: Actual cost incurred
            action_name: Name of the action that was executed
        
        Returns:
            Dictionary with keys:
                - success: bool indicating if action succeeded
                - status: updated harness status
                - metrics: updated metrics snapshot
                - corrective_prompt: JSON string with correction hint if failed
        """
        # Determine if action was successful
        is_success = self._evaluate_result(result)
        
        # Update metrics
        self._metrics.total_actions += 1
        if is_success:
            self._metrics.successful_actions += 1
        else:
            self._metrics.failed_actions += 1
        
        self._metrics.total_spend_usd += cost_usd
        self._metrics.total_tokens_used += tokens_used
        
        # Record error if failed
        if not is_success:
            error_msg = self._extract_error_message(result)
            self._metrics.errors.append(error_msg)
            self._last_error = error_msg
            logger.warning(f"Action failed: {action_name} - {error_msg}")
            
            # Keep only last 10 errors
            if len(self._metrics.errors) > 10:
                self._metrics.errors = self._metrics.errors[-10:]
        
        # Update status based on new metrics
        self._update_status()
        
        # Build response
        response = {
            "success": is_success,
            "status": self._status.value,
            "metrics": {
                "total_actions": self._metrics.total_actions,
                "successful_actions": self._metrics.successful_actions,
                "failed_actions": self._metrics.failed_actions,
                "error_rate": round(self._metrics.error_rate, 4),
                "success_rate": round(self._metrics.success_rate, 4),
                "total_spend_usd": round(self._metrics.total_spend_usd, 6),
                "total_tokens_used": self._metrics.total_tokens_used,
            },
            "corrective_prompt": None
        }
        
        # Generate corrective prompt if failed
        if not is_success:
            response["corrective_prompt"] = self.get_self_correction_prompt(
                action_name=action_name,
                error_message=self._last_error,
            )
        
        logger.info(
            f"Post-flight eval for {action_name}: success={is_success}, "
            f"duration={duration_ms}ms, tokens={tokens_used}, cost=${cost_usd:.6f}"
        )
        
        return response
    
    def _evaluate_result(self, result: Any) -> bool:
        """
        Evaluate whether a result indicates success or failure.
        
        Args:
            result: The result to evaluate
        
        Returns:
            True if success, False if failure
        """
        # If it's an exception, it's a failure
        if isinstance(result, Exception):
            return False
        
        # If it's a dict with 'error' key, check its value
        if isinstance(result, dict):
            if "error" in result and result["error"] is not None:
                return False
            if "status" in result and result["status"] in ["failure", "error", "failed"]:
                return False
            if "success" in result and result["success"] is False:
                return False
        
        # Default to success
        return True
    
    def _extract_error_message(self, result: Any) -> str:
        """
        Extract error message from a failed result.
        
        Args:
            result: The failed result
        
        Returns:
            Error message string
        """
        if isinstance(result, Exception):
            return f"{type(result).__name__}: {str(result)}"
        
        if isinstance(result, dict):
            if "error" in result:
                if isinstance(result["error"], dict):
                    return result["error"].get("message", str(result["error"]))
                return str(result["error"])
            if "message" in result:
                return str(result["message"])
        
        return f"Unknown error: {str(result)}"
    
    def get_self_correction_prompt(
        self,
        action_name: str = "",
        error_message: Optional[str] = None,
    ) -> str:
        """
        Generate a specific prompt to fix the agent if it failed.
        
        Returns a JSON-formatted string with a corrective_prompt field
        that suggests how the agent should retry the action.
        
        Args:
            action_name: Name of the failed action
            error_message: The error message from the failure
        
        Returns:
            JSON string with corrective_prompt field
        """
        error_msg = error_message or self._last_error or "Unknown error"
        
        # Build context-aware correction suggestions
        corrections = []
        
        # Budget-related corrections
        if "budget" in error_msg.lower() or "cost" in error_msg.lower():
            corrections.append(
                "Consider using a cheaper model or reducing token usage. "
                "Review your budget constraints before retrying."
            )
        
        # Token-related corrections
        if "token" in error_msg.lower():
            corrections.append(
                "Reduce the input size or split the task into smaller chunks. "
                "Consider summarizing long inputs before processing."
            )
        
        # Timeout-related corrections
        if "timeout" in error_msg.lower() or "time" in error_msg.lower():
            corrections.append(
                "The operation took too long. Consider breaking it into smaller steps "
                "or increasing the timeout threshold if appropriate."
            )
        
        # Rate limit corrections
        if "rate" in error_msg.lower() or "limit" in error_msg.lower():
            corrections.append(
                "You've hit a rate limit. Implement exponential backoff and retry "
                "after a delay. Consider batching requests."
            )
        
        # Generic corrections
        if not corrections:
            corrections.extend([
                "Review the error message carefully.",
                "Consider alternative approaches or parameters.",
                "Ensure all required inputs are valid and properly formatted.",
                "If this is a transient error, implement retry logic with backoff."
            ])
        
        # Build the corrective prompt structure
        correction_data = {
            "corrective_prompt": (
                f"Action '{action_name}' failed with error: {error_msg}. "
                f"Suggested corrections: {' '.join(corrections)} "
                f"Current harness status: {self._status.value}. "
                f"Error rate: {self._metrics.error_rate:.2%}. "
                f"Before retrying, ensure you address the root cause."
            ),
            "action_name": action_name,
            "error_message": error_msg,
            "suggestions": corrections,
            "harness_status": self._status.value,
            "error_rate": round(self._metrics.error_rate, 4),
            "retry_allowed": self._status != HarnessStatus.HALTED,
        }
        
        # Return as JSON string for agent parsing
        return json.dumps(correction_data, indent=2)
    
    def reset_metrics(self) -> Dict[str, Any]:
        """
        Reset all metrics to initial state.
        
        Returns:
            Confirmation dictionary
        """
        self._metrics = HarnessMetrics()
        self._status = HarnessStatus.READY
        self._last_error = None
        self._budget_warning_sent = False
        
        logger.info("Harness metrics reset to initial state")
        
        return {
            "reset": True,
            "status": self._status.value,
            "message": "All metrics have been reset"
        }
    
    def get_status_report(self) -> Dict[str, Any]:
        """
        Get a comprehensive status report.
        
        Returns:
            Dictionary with full status report
        """
        return {
            "status": self._status.value,
            "service_name": self.service_name,
            "environment": self.environment,
            "config": {
                "budget_limit_usd": self.config.budget_limit_usd,
                "max_tokens": self.config.max_tokens,
                "max_error_rate": self.config.max_error_rate,
                "timeout_ms": self.config.timeout_ms,
                "warning_budget_threshold": self.config.warning_budget_threshold,
                "max_actions_per_session": self.config.max_actions_per_session,
            },
            "metrics": {
                "total_actions": self._metrics.total_actions,
                "successful_actions": self._metrics.successful_actions,
                "failed_actions": self._metrics.failed_actions,
                "error_rate": round(self._metrics.error_rate, 4),
                "success_rate": round(self._metrics.success_rate, 4),
                "total_spend_usd": round(self._metrics.total_spend_usd, 6),
                "total_tokens_used": self._metrics.total_tokens_used,
                "recent_errors": self._metrics.errors[-5:],  # Last 5 errors
                "uptime_seconds": round(time.time() - self._metrics.start_time, 2),
            }
        }
    
    def check(self, **kwargs) -> Dict[str, Any]:
        """
        Simple API wrapper for pre_flight_check.
        
        Args:
            **kwargs: Arguments passed to pre_flight_check
        
        Returns:
            Result from pre_flight_check
        """
        return self.pre_flight_check(**kwargs)
    
    def evaluate(self, **kwargs) -> Dict[str, Any]:
        """
        Simple API wrapper for post_flight_eval.
        
        Args:
            **kwargs: Arguments passed to post_flight_eval
        
        Returns:
            Result from post_flight_eval
        """
        return self.post_flight_eval(**kwargs)


def with_harness(
    harness: AgentHarness,
    action_name: str = "",
    estimate_tokens: int = 0,
    estimate_cost: float = 0.0,
):
    """
    Decorator to wrap an agent function with the harness safety layer.
    
    Usage:
        >>> harness = AgentHarness(budget_limit_usd=10.0)
        >>> 
        >>> @with_harness(harness, action_name="llm.completion")
        >>> def call_llm(prompt: str):
        ...     # Your LLM call here
        ...     return result
    
    Args:
        harness: AgentHarness instance
        action_name: Name of the action
        estimate_tokens: Estimated tokens for pre-flight check
        estimate_cost: Estimated cost for pre-flight check
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Pre-flight check
            check_result = harness.pre_flight_check(
                action_name=action_name,
                estimated_tokens=estimate_tokens,
                estimated_cost_usd=estimate_cost,
            )
            
            if not check_result["allowed"]:
                logger.warning(f"Action blocked by harness: {check_result['reason']}")
                return {
                    "blocked": True,
                    "reason": check_result["reason"],
                    "harness_status": check_result["status"],
                }
            
            # Track start time
            start_time = time.time()
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Post-flight evaluation
                eval_result = harness.post_flight_eval(
                    result=result,
                    duration_ms=duration_ms,
                    action_name=action_name,
                )
                
                # Attach harness metadata to result
                if isinstance(result, dict):
                    result["_harness"] = eval_result
                else:
                    result = {"result": result, "_harness": eval_result}
                
                return result
                
            except Exception as e:
                # Handle exceptions
                duration_ms = (time.time() - start_time) * 1000
                eval_result = harness.post_flight_eval(
                    result=e,
                    duration_ms=duration_ms,
                    action_name=action_name,
                )
                
                return {
                    "error": str(e),
                    "exception_type": type(e).__name__,
                    "_harness": eval_result,
                }
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator
