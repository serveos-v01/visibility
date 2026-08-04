"""
Tests for the Agent Harness safety layer.

These tests verify:
- Budget blocking
- Error rate circuit breaking
- Self-correction prompt generation
- State transitions (Ready -> Warning -> Halted)
- Pre-flight and post-flight checks
- Metrics tracking
- Reset functionality
"""

import json
import pytest
from visibility.harness import (
    AgentHarness,
    HarnessConfig,
    HarnessStatus,
    HarnessMetrics,
    with_harness,
)


class TestHarnessConfig:
    """Test suite for HarnessConfig dataclass."""

    def test_default_config(self):
        """Test that default config has expected values."""
        config = HarnessConfig()
        assert config.budget_limit_usd is None
        assert config.max_tokens == 100000
        assert config.max_error_rate == 0.5
        assert config.timeout_ms == 30000
        assert config.warning_budget_threshold == 0.8
        assert config.max_actions_per_session == 1000

    def test_custom_config(self):
        """Test creating config with custom values."""
        config = HarnessConfig(
            budget_limit_usd=50.0,
            max_tokens=50000,
            max_error_rate=0.3,
            timeout_ms=10000,
            warning_budget_threshold=0.7,
            max_actions_per_session=500,
        )
        assert config.budget_limit_usd == 50.0
        assert config.max_tokens == 50000
        assert config.max_error_rate == 0.3
        assert config.timeout_ms == 10000
        assert config.warning_budget_threshold == 0.7
        assert config.max_actions_per_session == 500


class TestHarnessStatus:
    """Test suite for HarnessStatus enum."""

    def test_status_values(self):
        """Test that status enum has correct values."""
        assert HarnessStatus.READY.value == "READY"
        assert HarnessStatus.WARNING.value == "WARNING"
        assert HarnessStatus.HALTED.value == "HALTED"


class TestHarnessMetrics:
    """Test suite for HarnessMetrics dataclass."""

    def test_default_metrics(self):
        """Test that default metrics are zeroed."""
        metrics = HarnessMetrics()
        assert metrics.total_actions == 0
        assert metrics.successful_actions == 0
        assert metrics.failed_actions == 0
        assert metrics.total_spend_usd == 0.0
        assert metrics.total_tokens_used == 0
        assert len(metrics.errors) == 0
        assert metrics.error_rate == 0.0
        assert metrics.success_rate == 1.0

    def test_error_rate_calculation(self):
        """Test error rate calculation."""
        metrics = HarnessMetrics()
        metrics.total_actions = 10
        metrics.failed_actions = 3
        metrics.successful_actions = 7
        assert metrics.error_rate == 0.3
        assert metrics.success_rate == 0.7

    def test_error_rate_zero_division(self):
        """Test error rate handles zero actions."""
        metrics = HarnessMetrics()
        assert metrics.error_rate == 0.0
        assert metrics.success_rate == 1.0


class TestAgentHarnessInitialization:
    """Test suite for AgentHarness initialization."""

    def test_default_initialization(self):
        """Test harness initializes with defaults."""
        harness = AgentHarness()
        assert harness.status == HarnessStatus.READY
        assert harness.service_name == "visibility"
        assert harness.environment == "development"
        assert harness.config.budget_limit_usd is None
        assert harness.config.max_error_rate == 0.5

    def test_custom_initialization(self):
        """Test harness initializes with custom config."""
        config = HarnessConfig(budget_limit_usd=25.0, max_error_rate=0.2)
        harness = AgentHarness(
            config=config,
            service_name="test-service",
            environment="testing",
        )
        assert harness.config.budget_limit_usd == 25.0
        assert harness.config.max_error_rate == 0.2
        assert harness.service_name == "test-service"
        assert harness.environment == "testing"


class TestPreFlightCheck:
    """Test suite for pre_flight_check method."""

    def test_pre_flight_allowed_no_limits(self):
        """Test pre-flight passes when no limits set."""
        harness = AgentHarness()
        result = harness.pre_flight_check(action_name="test.action")
        assert result["allowed"] is True
        assert "passed" in result["reason"].lower()
        assert result["status"] == "READY"

    def test_pre_flight_blocked_when_halted(self):
        """Test pre-flight blocks when harness is halted."""
        harness = AgentHarness(config=HarnessConfig(max_error_rate=0.1))
        # Force halt by simulating errors
        harness._metrics.total_actions = 10
        harness._metrics.failed_actions = 2
        harness._update_status()
        
        result = harness.pre_flight_check(action_name="test.action")
        assert result["allowed"] is False
        assert "HALTED" in result["reason"]

    def test_pre_flight_budget_guard(self):
        """Test pre-flight blocks when budget would be exceeded."""
        harness = AgentHarness(config=HarnessConfig(budget_limit_usd=10.0))
        harness._metrics.total_spend_usd = 9.5
        
        # This should pass
        result = harness.pre_flight_check(estimated_cost_usd=0.4)
        assert result["allowed"] is True
        
        # This should fail
        result = harness.pre_flight_check(estimated_cost_usd=0.6)
        assert result["allowed"] is False
        assert "Budget guard" in result["reason"]

    def test_pre_flight_token_guard(self):
        """Test pre-flight blocks when tokens exceed limit."""
        harness = AgentHarness(config=HarnessConfig(max_tokens=1000))
        
        result = harness.pre_flight_check(estimated_tokens=1500)
        assert result["allowed"] is False
        assert "Token guard" in result["reason"]

    def test_pre_flight_error_rate_guard(self):
        """Test pre-flight blocks when error rate exceeds threshold."""
        harness = AgentHarness(config=HarnessConfig(max_error_rate=0.3))
        harness._metrics.total_actions = 10
        harness._metrics.failed_actions = 4  # 40% error rate
        
        result = harness.pre_flight_check()
        assert result["allowed"] is False
        assert "Error rate guard" in result["reason"]

    def test_pre_flight_max_actions_guard(self):
        """Test pre-flight blocks when action limit reached."""
        harness = AgentHarness(config=HarnessConfig(max_actions_per_session=5))
        harness._metrics.total_actions = 5
        
        result = harness.pre_flight_check()
        assert result["allowed"] is False
        assert "Action limit" in result["reason"]

    def test_pre_flight_includes_metrics(self):
        """Test pre-flight response includes current metrics."""
        harness = AgentHarness()
        harness._metrics.total_actions = 10
        harness._metrics.total_spend_usd = 5.5
        harness._metrics.total_tokens_used = 1000
        
        result = harness.pre_flight_check()
        assert "metrics" in result
        assert result["metrics"]["total_actions"] == 10
        assert result["metrics"]["total_spend_usd"] == 5.5
        assert result["metrics"]["total_tokens_used"] == 1000


class TestPostFlightEval:
    """Test suite for post_flight_eval method."""

    def test_post_flight_success_dict_result(self):
        """Test post-flight evaluates successful dict result."""
        harness = AgentHarness()
        result = {"data": "success", "status": "success"}
        
        eval_result = harness.post_flight_eval(
            result=result,
            duration_ms=100,
            tokens_used=50,
            cost_usd=0.01,
            action_name="test.action",
        )
        
        assert eval_result["success"] is True
        assert harness.metrics.successful_actions == 1
        assert harness.metrics.total_spend_usd == 0.01
        assert harness.metrics.total_tokens_used == 50

    def test_post_flight_failure_exception(self):
        """Test post-flight evaluates exception as failure."""
        harness = AgentHarness()
        error = ValueError("Test error")
        
        eval_result = harness.post_flight_eval(
            result=error,
            duration_ms=100,
            action_name="test.action",
        )
        
        assert eval_result["success"] is False
        assert harness.metrics.failed_actions == 1
        assert len(harness.metrics.errors) == 1

    def test_post_flight_failure_dict_with_error(self):
        """Test post-flight evaluates dict with error key as failure."""
        harness = AgentHarness()
        result = {"error": "Something went wrong"}
        
        eval_result = harness.post_flight_eval(
            result=result,
            duration_ms=100,
            action_name="test.action",
        )
        
        assert eval_result["success"] is False

    def test_post_flight_failure_dict_with_status(self):
        """Test post-flight evaluates dict with failure status."""
        harness = AgentHarness()
        result = {"status": "failure", "data": "partial"}
        
        eval_result = harness.post_flight_eval(
            result=result,
            duration_ms=100,
            action_name="test.action",
        )
        
        assert eval_result["success"] is False

    def test_post_flight_generates_corrective_prompt(self):
        """Test post-flight generates corrective prompt on failure."""
        harness = AgentHarness()
        error = RuntimeError("Rate limit exceeded")
        
        eval_result = harness.post_flight_eval(
            result=error,
            duration_ms=100,
            action_name="test.action",
        )
        
        assert eval_result["corrective_prompt"] is not None
        correction_data = json.loads(eval_result["corrective_prompt"])
        assert "corrective_prompt" in correction_data
        assert "rate limit" in correction_data["corrective_prompt"].lower()

    def test_post_flight_updates_status_on_budget_exceeded(self):
        """Test post-flight updates status to HALTED when budget exceeded."""
        harness = AgentHarness(config=HarnessConfig(budget_limit_usd=10.0))
        
        # Simulate spending that exceeds budget
        eval_result = harness.post_flight_eval(
            result={"status": "success"},
            duration_ms=100,
            cost_usd=15.0,
            action_name="expensive.action",
        )
        
        assert harness.status == HarnessStatus.HALTED
        assert eval_result["status"] == "HALTED"


class TestCircuitBreaker:
    """Test suite for circuit breaker functionality."""

    def test_circuit_breaker_triggers_on_error_rate(self):
        """Test circuit breaker halts when error rate exceeds threshold."""
        harness = AgentHarness(config=HarnessConfig(max_error_rate=0.3))
        
        # Simulate 3 failures out of 10 actions (30% error rate)
        for i in range(7):
            harness.post_flight_eval(result={"status": "success"}, duration_ms=10)
        
        assert harness.status == HarnessStatus.READY
        
        # Add failures to trigger circuit breaker
        for i in range(3):
            harness.post_flight_eval(result=Exception("Error"), duration_ms=10)
        
        assert harness.status == HarnessStatus.HALTED

    def test_circuit_breaker_blocks_after_trigger(self):
        """Test that actions are blocked after circuit breaker triggers."""
        harness = AgentHarness(config=HarnessConfig(max_error_rate=0.2))
        
        # Trigger circuit breaker
        for i in range(2):
            harness.post_flight_eval(result=Exception("Error"), duration_ms=10)
        
        assert harness.status == HarnessStatus.HALTED
        
        # Try to perform new action
        check_result = harness.pre_flight_check(action_name="new.action")
        assert check_result["allowed"] is False


class TestStateTransitions:
    """Test suite for state transitions."""

    def test_ready_to_warning_transition(self):
        """Test transition from READY to WARNING on budget threshold."""
        harness = AgentHarness(
            config=HarnessConfig(budget_limit_usd=10.0, warning_budget_threshold=0.8)
        )
        
        assert harness.status == HarnessStatus.READY
        
        # Spend 80% of budget
        harness.post_flight_eval(
            result={"status": "success"},
            duration_ms=100,
            cost_usd=8.0,
            action_name="spend.action",
        )
        
        assert harness.status == HarnessStatus.WARNING

    def test_warning_to_halted_transition(self):
        """Test transition from WARNING to HALTED on budget exceeded."""
        harness = AgentHarness(
            config=HarnessConfig(budget_limit_usd=10.0, warning_budget_threshold=0.8)
        )
        
        # First go to WARNING
        harness.post_flight_eval(
            result={"status": "success"},
            duration_ms=100,
            cost_usd=8.0,
            action_name="spend.action",
        )
        assert harness.status == HarnessStatus.WARNING
        
        # Then exceed budget
        harness.post_flight_eval(
            result={"status": "success"},
            duration_ms=100,
            cost_usd=3.0,
            action_name="spend_more.action",
        )
        
        assert harness.status == HarnessStatus.HALTED

    def test_ready_to_halted_direct_on_error_rate(self):
        """Test direct transition from READY to HALTED on error rate."""
        harness = AgentHarness(config=HarnessConfig(max_error_rate=0.5))
        
        # 50% error rate immediately triggers HALT
        harness.post_flight_eval(result=Exception("Error"), duration_ms=10)
        harness.post_flight_eval(result={"status": "success"}, duration_ms=10)
        
        assert harness.status == HarnessStatus.HALTED


class TestSelfCorrectionPrompt:
    """Test suite for self-correction prompt generation."""

    def test_self_correction_returns_valid_json(self):
        """Test that self-correction prompt is valid JSON."""
        harness = AgentHarness()
        harness._last_error = "Test error"
        
        prompt_str = harness.get_self_correction_prompt(action_name="test.action")
        
        # Should be parseable JSON
        prompt_data = json.loads(prompt_str)
        assert isinstance(prompt_data, dict)

    def test_self_correction_includes_required_fields(self):
        """Test that self-correction prompt includes all required fields."""
        harness = AgentHarness()
        harness._last_error = "Connection timeout"
        
        prompt_str = harness.get_self_correction_prompt(action_name="api.call")
        prompt_data = json.loads(prompt_str)
        
        assert "corrective_prompt" in prompt_data
        assert "action_name" in prompt_data
        assert "error_message" in prompt_data
        assert "suggestions" in prompt_data
        assert "harness_status" in prompt_data
        assert "retry_allowed" in prompt_data

    def test_self_correction_budget_hint(self):
        """Test self-correction provides budget-specific hints."""
        harness = AgentHarness()
        harness._last_error = "Budget exceeded for this month"
        
        prompt_str = harness.get_self_correction_prompt()
        prompt_data = json.loads(prompt_str)
        
        assert "cheaper model" in prompt_data["corrective_prompt"].lower() or \
               "budget" in prompt_data["corrective_prompt"].lower()

    def test_self_correction_token_hint(self):
        """Test self-correction provides token-specific hints."""
        harness = AgentHarness()
        harness._last_error = "Token limit exceeded"
        
        prompt_str = harness.get_self_correction_prompt()
        prompt_data = json.loads(prompt_str)
        
        assert any("token" in s.lower() for s in prompt_data["suggestions"]) or \
               "token" in prompt_data["corrective_prompt"].lower()

    def test_self_correction_rate_limit_hint(self):
        """Test self-correction provides rate-limit-specific hints."""
        harness = AgentHarness()
        harness._last_error = "Rate limit exceeded: 429 Too Many Requests"
        
        prompt_str = harness.get_self_correction_prompt()
        prompt_data = json.loads(prompt_str)
        
        assert "backoff" in prompt_data["corrective_prompt"].lower() or \
               "rate" in prompt_data["corrective_prompt"].lower()


class TestResetMetrics:
    """Test suite for reset_metrics method."""

    def test_reset_clears_all_metrics(self):
        """Test reset clears all accumulated metrics."""
        harness = AgentHarness()
        
        # Accumulate some metrics
        for i in range(5):
            harness.post_flight_eval(
                result={"status": "success"} if i % 2 == 0 else Exception("Error"),
                duration_ms=100,
                cost_usd=0.5,
                tokens_used=100,
            )
        
        assert harness.metrics.total_actions == 5
        
        # Reset
        result = harness.reset_metrics()
        
        assert result["reset"] is True
        assert harness.metrics.total_actions == 0
        assert harness.metrics.total_spend_usd == 0.0
        assert harness.metrics.total_tokens_used == 0
        assert len(harness.metrics.errors) == 0

    def test_reset_resets_status(self):
        """Test reset returns status to READY."""
        harness = AgentHarness(config=HarnessConfig(max_error_rate=0.1))
        
        # Force HALT
        harness._metrics.failed_actions = 5
        harness._metrics.total_actions = 10
        harness._update_status()
        assert harness.status == HarnessStatus.HALTED
        
        # Reset
        harness.reset_metrics()
        assert harness.status == HarnessStatus.READY


class TestGetStatusReport:
    """Test suite for get_status_report method."""

    def test_status_report_structure(self):
        """Test status report has expected structure."""
        harness = AgentHarness(
            config=HarnessConfig(budget_limit_usd=50.0),
            service_name="test-svc",
            environment="prod",
        )
        
        report = harness.get_status_report()
        
        assert "status" in report
        assert "service_name" in report
        assert "environment" in report
        assert "config" in report
        assert "metrics" in report
        
        assert report["service_name"] == "test-svc"
        assert report["environment"] == "prod"
        assert report["config"]["budget_limit_usd"] == 50.0

    def test_status_report_includes_recent_errors(self):
        """Test status report includes recent errors."""
        harness = AgentHarness()
        
        # Generate some errors
        for i in range(7):
            harness.post_flight_eval(result=Exception(f"Error {i}"), duration_ms=10)
        
        report = harness.get_status_report()
        
        assert "recent_errors" in report["metrics"]
        assert len(report["metrics"]["recent_errors"]) <= 5


class TestSimpleAPI:
    """Test suite for simple API methods (check/evaluate)."""

    def test_check_wrapper(self):
        """Test check() wraps pre_flight_check()."""
        harness = AgentHarness()
        
        check_result = harness.check(action_name="test")
        pre_result = harness.pre_flight_check(action_name="test")
        
        assert check_result == pre_result

    def test_evaluate_wrapper(self):
        """Test evaluate() wraps post_flight_eval()."""
        harness = AgentHarness()
        
        eval_result = harness.evaluate(
            result={"status": "success"},
            duration_ms=100,
            action_name="test",
        )
        
        assert eval_result["success"] is True


class TestWithHarnessDecorator:
    """Test suite for with_harness decorator."""

    def test_decorator_allows_successful_function(self):
        """Test decorator allows successful function execution."""
        harness = AgentHarness()
        
        @with_harness(harness, action_name="test.func")
        def success_func():
            return {"result": "success"}
        
        result = success_func()
        assert "_harness" in result
        assert result["_harness"]["success"] is True

    def test_decorator_handles_exception(self):
        """Test decorator handles exceptions gracefully."""
        harness = AgentHarness()
        
        @with_harness(harness, action_name="test.func")
        def failing_func():
            raise ValueError("Test error")
        
        result = failing_func()
        assert "error" in result
        assert result["error"] == "Test error"
        assert "_harness" in result
        assert result["_harness"]["success"] is False

    def test_decorator_blocks_when_halted(self):
        """Test decorator blocks execution when harness is halted."""
        harness = AgentHarness(config=HarnessConfig(max_error_rate=0.1))
        
        # Force halt
        harness._metrics.failed_actions = 1
        harness._metrics.total_actions = 1
        harness._update_status()
        
        @with_harness(harness, action_name="test.func")
        def any_func():
            return {"result": "success"}
        
        result = any_func()
        assert result["blocked"] is True
        assert "HALTED" in result["reason"]


class TestJSONOutput:
    """Test suite for JSON output compliance."""

    def test_pre_flight_output_is_json_serializable(self):
        """Test pre_flight_check output is JSON serializable."""
        harness = AgentHarness(config=HarnessConfig(budget_limit_usd=10.0))
        harness._metrics.total_spend_usd = 9.0
        
        result = harness.pre_flight_check(estimated_cost_usd=2.0)
        
        # Should not raise
        json_str = json.dumps(result)
        assert isinstance(json_str, str)

    def test_post_flight_output_is_json_serializable(self):
        """Test post_flight_eval output is JSON serializable."""
        harness = AgentHarness()
        
        result = harness.post_flight_eval(
            result={"status": "success"},
            duration_ms=100,
            action_name="test",
        )
        
        # Should not raise
        json_str = json.dumps(result)
        assert isinstance(json_str, str)

    def test_get_status_report_is_json_serializable(self):
        """Test get_status_report output is JSON serializable."""
        harness = AgentHarness()
        
        report = harness.get_status_report()
        
        # Should not raise
        json_str = json.dumps(report)
        assert isinstance(json_str, str)
