"""
Functional tests for the Visibility tracker.

These tests verify core tracking functionality including:
- Request tracking
- Error tracking
- LLM token tracking
- Budget monitoring
- Event querying
- Summary generation
"""

import os
import tempfile
import pytest
from pathlib import Path

from visibility.tracker import Visibility
from visibility.events import create_event, EVENT_TYPES
from visibility.schemas import get_openai_tool_schema, get_mcp_manifest


@pytest.fixture
def temp_db():
    """Create a temporary database file for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_visibility.db")
        yield db_path


@pytest.fixture
def tracker(temp_db):
    """Create a Visibility tracker instance with temporary database."""
    tracker = Visibility(
        service_name="test-service",
        environment="testing",
        db_path=temp_db,
        enable_console=False,
    )
    yield tracker
    tracker.close()


class TestVisibilityTracker:
    """Test suite for Visibility tracker core functionality."""

    def test_tracker_initialization(self, temp_db):
        """Test that tracker initializes correctly."""
        tracker = Visibility(
            service_name="test-service",
            environment="testing",
            db_path=temp_db,
        )
        assert tracker.service_name == "test-service"
        assert tracker.environment == "testing"
        assert tracker.db_path == temp_db
        tracker.close()

    def test_track_request(self, tracker):
        """Test tracking an API request event."""
        event = tracker.track_request(
            name="api.users.list",
            method="GET",
            url="/api/v1/users",
            route="/api/v1/users",
            status_code=200,
            duration_ms=45.5,
            tags=["api", "users"],
        )
        
        assert event["type"] == "request"
        assert event["name"] == "api.users.list"
        assert event["level"] == "info"
        assert event["status"] == "success"
        assert event["duration_ms"] == 45.5
        assert event["request"]["method"] == "GET"
        assert event["request"]["url"] == "/api/v1/users"
        assert event["request"]["status_code"] == 200
        assert "id" in event
        assert "timestamp" in event
        assert "sdk" in event

    def test_track_request_failure(self, tracker):
        """Test tracking a failed API request."""
        event = tracker.track_request(
            name="api.users.get",
            method="GET",
            url="/api/v1/users/999",
            status_code=404,
        )
        
        assert event["type"] == "request"
        assert event["status"] == "failure"
        assert event["request"]["status_code"] == 404

    def test_track_error(self, tracker):
        """Test tracking an error event."""
        event = tracker.track_error(
            name="database.connection.failed",
            message="Connection timeout after 30s",
            error_name="ConnectionError",
            stack="Traceback (most recent call last):\n  ...",
            code="DB_TIMEOUT",
            duration_ms=30000,
            tags=["database", "critical"],
        )
        
        assert event["type"] == "error"
        assert event["name"] == "database.connection.failed"
        assert event["level"] == "error"
        assert event["status"] == "failure"
        assert event["error"]["message"] == "Connection timeout after 30s"
        assert event["error"]["name"] == "ConnectionError"
        assert event["error"]["code"] == "DB_TIMEOUT"

    def test_track_llm(self, tracker):
        """Test tracking an LLM call event."""
        event = tracker.track_llm(
            name="llm.completion",
            provider="openai",
            model="gpt-4-turbo",
            prompt_tokens=150,
            completion_tokens=75,
            agent_id="agent-001",
            session_id="session-abc",
            duration_ms=1200,
            tags=["llm", "completion"],
        )
        
        assert event["type"] == "llm"
        assert event["name"] == "llm.completion"
        assert event["llm"]["provider"] == "openai"
        assert event["llm"]["model"] == "gpt-4-turbo"
        assert event["llm"]["prompt_tokens"] == 150
        assert event["llm"]["completion_tokens"] == 75
        assert event["llm"]["total_tokens"] == 225
        assert event["llm"]["agent_id"] == "agent-001"
        assert event["llm"]["session_id"] == "session-abc"

    def test_track_llm_with_cost(self, temp_db):
        """Test LLM tracking with cost calculation."""
        tracker = Visibility(
            service_name="test-service",
            db_path=temp_db,
            token_cost_rules=[
                {
                    "match_model": "gpt-4-turbo",
                    "prompt_usd_per_1k": 0.01,
                    "completion_usd_per_1k": 0.03,
                }
            ],
        )
        
        event = tracker.track_llm(
            name="llm.cost_test",
            model="gpt-4-turbo",
            prompt_tokens=1000,
            completion_tokens=500,
        )
        
        # Cost should be: (1000/1000)*0.01 + (500/1000)*0.03 = 0.01 + 0.015 = 0.025
        assert event["llm"]["estimated_cost_usd"] == 0.025
        tracker.close()

    def test_track_custom(self, tracker):
        """Test tracking a custom event."""
        event = tracker.track_custom(
            name="user.action.completed",
            level="info",
            status="success",
            duration_ms=100,
            context={"user_id": "user-123", "action": "purchase"},
            tags=["custom", "user"],
        )
        
        assert event["type"] == "custom"
        assert event["name"] == "user.action.completed"
        assert event["context"]["user_id"] == "user-123"

    def test_query_events(self, tracker):
        """Test querying events from storage."""
        # Track multiple events
        tracker.track_request(name="api.test.1", method="GET", url="/test1")
        tracker.track_request(name="api.test.2", method="POST", url="/test2")
        tracker.track_error(name="error.test", message="Test error")
        
        # Query all events
        all_events = tracker.query(limit=100)
        assert len(all_events) == 3
        
        # Query by type
        request_events = tracker.query(event_type="request", limit=100)
        assert len(request_events) == 2
        
        # Query by name
        specific_event = tracker.query(name="api.test.1", limit=100)
        assert len(specific_event) == 1

    def test_summary(self, tracker):
        """Test generating a summary report."""
        # Track some events
        tracker.track_request(name="api.test", method="GET", url="/test")
        tracker.track_llm(
            name="llm.test",
            provider="openai",
            model="gpt-4",
            prompt_tokens=100,
            completion_tokens=50,
        )
        
        summary = tracker.summary()
        
        assert "total_events" in summary
        assert "total_requests" in summary
        assert "total_llm_calls" in summary
        assert "estimated_cost_usd" in summary
        assert summary["total_events"] >= 2

    def test_context_manager(self, temp_db):
        """Test using tracker as a context manager."""
        with Visibility(service_name="test", db_path=temp_db) as tracker:
            tracker.track_request(name="context.test", method="GET", url="/test")
            events = tracker.query(limit=100)
            assert len(events) == 1
        # Tracker should be closed after context exit

    def test_budget_warning(self, temp_db):
        """Test budget warning functionality."""
        tracker = Visibility(
            service_name="test-service",
            db_path=temp_db,
            monthly_usd_limit=10.0,
            warning_threshold=0.8,
            token_cost_rules=[
                {
                    "match_model": "expensive-model",
                    "prompt_usd_per_1k": 1.0,
                    "completion_usd_per_1k": 2.0,
                }
            ],
        )
        
        # Track LLM calls that exceed threshold
        tracker.track_llm(
            name="llm.expensive",
            model="expensive-model",
            prompt_tokens=5000,  # $5
            completion_tokens=2000,  # $4
        )
        
        # Query for budget events
        budget_events = tracker.query(event_type="budget", limit=100)
        assert len(budget_events) >= 1
        assert any(e["name"] == "budget.warning" for e in budget_events)
        
        tracker.close()


class TestSchemas:
    """Test suite for OpenAI and MCP schema generation."""

    def test_openai_tool_schema_structure(self):
        """Test that OpenAI tool schema has correct structure."""
        schema = get_openai_tool_schema()
        
        assert "tools" in schema
        assert isinstance(schema["tools"], list)
        assert len(schema["tools"]) == 3
        
        tool_names = [t["function"]["name"] for t in schema["tools"]]
        assert "visibility_track" in tool_names
        assert "visibility_query" in tool_names
        assert "visibility_summary" in tool_names

    def test_mcp_manifest_structure(self):
        """Test that MCP manifest has correct structure."""
        manifest = get_mcp_manifest()
        
        assert "name" in manifest
        assert "version" in manifest
        assert "description" in manifest
        assert "tools" in manifest
        
        assert manifest["name"] == "visibility"
        assert manifest["version"] == "0.1.0"

    def test_openai_track_function_schema(self):
        """Test the visibility_track function schema details."""
        schema = get_openai_tool_schema()
        track_func = None
        
        for tool in schema["tools"]:
            if tool["function"]["name"] == "visibility_track":
                track_func = tool["function"]
                break
        
        assert track_func is not None
        assert "description" in track_func
        assert "parameters" in track_func
        
        params = track_func["parameters"]
        assert params["type"] == "object"
        assert "properties" in params
        assert "required" in params
        assert "type" in params["required"]
        assert "name" in params["required"]

    def test_event_types_in_schema(self):
        """Test that schema includes all event types."""
        schema = get_openai_tool_schema()
        track_func = None
        
        for tool in schema["tools"]:
            if tool["function"]["name"] == "visibility_track":
                track_func = tool["function"]
                break
        
        type_enum = track_func["parameters"]["properties"]["type"]["enum"]
        for event_type in EVENT_TYPES:
            assert event_type in type_enum


class TestCreateEvent:
    """Test suite for event creation."""

    def test_create_basic_event(self):
        """Test creating a basic event."""
        event = create_event(event_type="custom", name="test.event")
        
        assert event["type"] == "custom"
        assert event["name"] == "test.event"
        assert event["level"] == "info"
        assert "id" in event
        assert "timestamp" in event
        assert "sdk" in event

    def test_create_event_with_all_fields(self):
        """Test creating an event with all optional fields."""
        event = create_event(
            event_type="request",
            name="test.full",
            level="warn",
            status="failure",
            duration_ms=100.5,
            request={"method": "GET"},
            context={"key": "value"},
            tags=["tag1", "tag2"],
        )
        
        assert event["level"] == "warn"
        assert event["status"] == "failure"
        assert event["duration_ms"] == 100.5
        assert event["request"]["method"] == "GET"
        assert event["context"]["key"] == "value"
        assert event["tags"] == ["tag1", "tag2"]

    def test_create_event_invalid_type(self):
        """Test that invalid event types raise ValueError."""
        with pytest.raises(ValueError, match="Invalid event type"):
            create_event(event_type="invalid_type", name="test")

    def test_create_event_invalid_level(self):
        """Test that invalid log levels raise ValueError."""
        with pytest.raises(ValueError, match="Invalid level"):
            create_event(event_type="custom", name="test", level="invalid")

    def test_create_event_invalid_status(self):
        """Test that invalid status values raise ValueError."""
        with pytest.raises(ValueError, match="Invalid status"):
            create_event(event_type="custom", name="test", status="invalid")
