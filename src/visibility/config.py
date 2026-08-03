"""
Configuration module for Visibility.

Stores configuration, provides defaults, supports budget limits,
redaction keys, token cost rules, and storage path.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class VisibilityConfig:
    """Configuration for Visibility tracker."""
    
    service_name: str = "visibility"
    environment: str = "development"
    db_path: str = ".visibility/visibility.db"
    enabled: bool = True
    sample_rate: float = 1.0
    redact_keys: List[str] = field(default_factory=lambda: [
        "authorization",
        "token",
        "api_key",
        "access_token",
        "refresh_token",
        "password",
        "secret"
    ])
    monthly_usd_limit: Optional[float] = None
    warning_threshold: float = 0.8
    token_cost_rules: List[Dict] = field(default_factory=lambda: [
        {
            "match_model": "gpt-4o-mini",
            "prompt_usd_per_1k": 0.00015,
            "completion_usd_per_1k": 0.0006
        },
        {
            "match_model": "gpt-4o",
            "prompt_usd_per_1k": 0.005,
            "completion_usd_per_1k": 0.015
        }
    ])
