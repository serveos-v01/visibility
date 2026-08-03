"""
Events module for Visibility.

Creates event dictionaries, validates required fields,
generates UUID and UTC timestamp, attaches SDK metadata,
and ensures JSON serializability.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List


# Event types
EVENT_TYPES = ["request", "error", "llm", "metric", "trace", "budget", "custom"]

# Log levels
LOG_LEVELS = ["debug", "info", "warn", "error"]

# Status values
STATUS_VALUES = ["success", "failure"]

# SDK metadata
SDK_NAME = "visibility"
SDK_VERSION = "0.1.0"


def create_event(
    event_type: str,
    name: str,
    level: str = "info",
    status: Optional[str] = None,
    duration_ms: Optional[float] = None,
    request: Optional[Dict[str, Any]] = None,
    error: Optional[Dict[str, Any]] = None,
    llm: Optional[Dict[str, Any]] = None,
    budget: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Create a new event dictionary.
    
    Args:
        event_type: Type of event (request, error, llm, metric, trace, budget, custom)
        name: Stable event name
        level: Log level (debug, info, warn, error)
        status: Status (success, failure, or None)
        duration_ms: Duration in milliseconds
        request: Request object
        error: Error object
        llm: LLM object
        budget: Budget object
        context: Context object
        tags: List of tags
    
    Returns:
        JSON-serializable event dictionary
    """
    # Validate event type
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Invalid event type: {event_type}. Must be one of {EVENT_TYPES}")
    
    # Validate level
    if level not in LOG_LEVELS:
        raise ValueError(f"Invalid level: {level}. Must be one of {LOG_LEVELS}")
    
    # Validate status if provided
    if status is not None and status not in STATUS_VALUES:
        raise ValueError(f"Invalid status: {status}. Must be one of {STATUS_VALUES}")
    
    # Generate event
    event = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "name": name,
        "level": level,
        "status": status,
        "duration_ms": duration_ms,
        "request": request,
        "error": error,
        "llm": llm,
        "budget": budget,
        "context": context,
        "tags": tags or [],
        "sdk": {
            "name": SDK_NAME,
            "version": SDK_VERSION
        }
    }
    
    return event
