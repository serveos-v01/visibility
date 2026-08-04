"""
Usage Example: Agent Harness Safety Layer for Visibility SDK

This script demonstrates how to integrate the Agent Harness safety layer
with your AI agent functions to ensure budget compliance, error recovery,
and automatic circuit breaking.
"""

from visibility import AgentHarness, HarnessConfig, with_harness


# =============================================================================
# Example 1: Basic Harness Setup
# =============================================================================

def example_basic_usage():
    """Demonstrate basic harness usage with pre-flight and post-flight checks."""
    
    # Initialize harness with budget limit and error rate threshold
    harness = AgentHarness(
        config=HarnessConfig(
            budget_limit_usd=10.0,      # Max $10 per session
            max_error_rate=0.3,         # Halt if >30% errors
            max_tokens=50000,           # Max 50k tokens per action
            warning_budget_threshold=0.8,  # Warn at 80% budget
        ),
        service_name="my-agent",
        environment="production",
    )
    
    # Simulate an agent action
    action_name = "llm.completion"
    
    # Pre-flight check before executing action
    check_result = harness.pre_flight_check(
        action_name=action_name,
        estimated_tokens=1000,
        estimated_cost_usd=0.05,
    )
    
    if not check_result["allowed"]:
        print(f"Action blocked: {check_result['reason']}")
        return
    
    # Execute your agent action here
    # result = call_your_llm_api(...)
    result = {"status": "success", "data": "response"}
    duration_ms = 1500
    tokens_used = 950
    cost_usd = 0.04
    
    # Post-flight evaluation after execution
    eval_result = harness.post_flight_eval(
        result=result,
        duration_ms=duration_ms,
        tokens_used=tokens_used,
        cost_usd=cost_usd,
        action_name=action_name,
    )
    
    if not eval_result["success"]:
        # Get self-correction prompt for retry
        correction = eval_result["corrective_prompt"]
        print(f"Action failed. Correction hint: {correction}")
    
    # Check current status
    print(f"Harness status: {harness.status.value}")
    print(f"Error rate: {harness.metrics.error_rate:.2%}")


# =============================================================================
# Example 2: Using the Decorator
# =============================================================================

def example_decorator_usage():
    """Demonstrate using the @with_harness decorator for automatic wrapping."""
    
    # Initialize harness
    harness = AgentHarness(
        config=HarnessConfig(budget_limit_usd=5.0, max_error_rate=0.5),
        service_name="decorated-agent",
    )
    
    # Wrap your function with the harness
    @with_harness(harness, action_name="agent.search", estimate_tokens=500)
    def search_knowledge_base(query: str):
        """Search the knowledge base for relevant information."""
        # Your implementation here
        return {"results": ["result1", "result2"], "status": "success"}
    
    # Call the wrapped function - harness automatically handles pre/post checks
    result = search_knowledge_base("What is the weather?")
    
    if "blocked" in result and result["blocked"]:
        print(f"Function was blocked: {result['reason']}")
    else:
        print(f"Function executed successfully: {result.get('results')}")
        print(f"Harness metrics: {result.get('_harness', {}).get('metrics')}")


# =============================================================================
# Example 3: Circuit Breaker Pattern
# =============================================================================

def example_circuit_breaker():
    """Demonstrate automatic circuit breaking on high error rates."""
    
    harness = AgentHarness(
        config=HarnessConfig(max_error_rate=0.2),  # Halt at 20% errors
    )
    
    # Simulate a series of actions with failures
    for i in range(10):
        # Alternate between success and failure
        if i % 3 == 0:
            result = Exception("API timeout")
        else:
            result = {"status": "success"}
        
        eval_result = harness.post_flight_eval(
            result=result,
            duration_ms=100,
            action_name=f"action_{i}",
        )
        
        print(f"Action {i}: status={harness.status.value}, "
              f"error_rate={harness.metrics.error_rate:.2%}")
        
        # Once halted, all further actions will be blocked
        if harness.status.value == "HALTED":
            print(f"Circuit breaker triggered at action {i}!")
            break
    
    # Try to perform new action after halt
    check = harness.pre_flight_check(action_name="next_action")
    print(f"Next action allowed: {check['allowed']}")
    print(f"Reason: {check['reason']}")


# =============================================================================
# Example 4: Self-Correction Prompts
# =============================================================================

def example_self_correction():
    """Demonstrate getting self-correction prompts for failed actions."""
    
    harness = AgentHarness()
    
    # Simulate different types of failures
    failures = [
        ("Budget exceeded", "Your monthly budget of $10 has been exceeded"),
        ("Token limit", "Token limit exceeded: requested 150000, max 100000"),
        ("Rate limit", "Rate limit exceeded: 429 Too Many Requests"),
        ("Timeout", "Request timeout after 30000ms"),
    ]
    
    for error_name, error_msg in failures:
        harness._last_error = error_msg
        
        correction_json = harness.get_self_correction_prompt(
            action_name="agent.task",
        )
        
        print(f"\n=== {error_name} ===")
        print(f"Correction prompt: {correction_json}")


# =============================================================================
# Example 5: Integration with Visibility Tracker
# =============================================================================

def example_integration_with_tracker():
    """Demonstrate integrating harness with Visibility tracker."""
    
    from visibility import Visibility, AgentHarness, HarnessConfig
    
    # Initialize both tracker and harness
    tracker = Visibility(
        service_name="integrated-agent",
        db_path=".visibility/integrated.db",
        monthly_usd_limit=20.0,
    )
    
    harness = AgentHarness(
        config=HarnessConfig(
            budget_limit_usd=20.0,
            max_error_rate=0.3,
        ),
        service_name="integrated-agent",
    )
    
    # Use harness for pre-flight check
    check = harness.check(
        action_name="llm.completion",
        estimated_cost_usd=0.10,
    )
    
    if check["allowed"]:
        # Track LLM call with visibility
        event = tracker.track_llm(
            name="llm.completion",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=500,
            completion_tokens=200,
            duration_ms=1200,
        )
        
        # Evaluate with harness
        harness.evaluate(
            result={"status": "success"},
            duration_ms=1200,
            tokens_used=700,
            cost_usd=event["llm"]["estimated_cost_usd"],
            action_name="llm.completion",
        )
    
    # Get combined status
    print(f"Harness status: {harness.status.value}")
    summary = tracker.summary()
    print(f"Total spend: ${summary['estimated_cost_usd']:.4f}")
    
    tracker.close()


# =============================================================================
# Example 6: Status Monitoring and Reset
# =============================================================================

def example_monitoring_and_reset():
    """Demonstrate monitoring harness status and resetting metrics."""
    
    harness = AgentHarness(
        config=HarnessConfig(budget_limit_usd=10.0),
        service_name="monitored-agent",
    )
    
    # Simulate some actions
    for i in range(5):
        harness.post_flight_eval(
            result={"status": "success"},
            duration_ms=100,
            cost_usd=0.50,
            action_name=f"action_{i}",
        )
    
    # Get comprehensive status report
    report = harness.get_status_report()
    print("Status Report:")
    print(f"  Status: {report['status']}")
    print(f"  Total Actions: {report['metrics']['total_actions']}")
    print(f"  Success Rate: {report['metrics']['success_rate']:.2%}")
    print(f"  Total Spend: ${report['metrics']['total_spend_usd']:.4f}")
    print(f"  Uptime: {report['metrics']['uptime_seconds']}s")
    
    # Reset metrics for new session
    reset_result = harness.reset_metrics()
    print(f"\nMetrics reset: {reset_result['reset']}")
    print(f"New status: {harness.status.value}")


if __name__ == "__main__":
    print("=" * 70)
    print("Example 1: Basic Usage")
    print("=" * 70)
    example_basic_usage()
    
    print("\n" + "=" * 70)
    print("Example 2: Decorator Usage")
    print("=" * 70)
    example_decorator_usage()
    
    print("\n" + "=" * 70)
    print("Example 3: Circuit Breaker")
    print("=" * 70)
    example_circuit_breaker()
    
    print("\n" + "=" * 70)
    print("Example 4: Self-Correction Prompts")
    print("=" * 70)
    example_self_correction()
    
    print("\n" + "=" * 70)
    print("Example 5: Integration with Tracker")
    print("=" * 70)
    example_integration_with_tracker()
    
    print("\n" + "=" * 70)
    print("Example 6: Monitoring and Reset")
    print("=" * 70)
    example_monitoring_and_reset()
