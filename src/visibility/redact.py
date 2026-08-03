"""
Redaction module for Visibility.

Recursively redacts sensitive keys in dictionaries and lists.
Replaces secret values with "[REDACTED]".
"""

from typing import Any, List


def redact_sensitive_data(data: Any, sensitive_keys: List[str]) -> Any:
    """
    Recursively redact sensitive keys in a dictionary or list.
    
    Args:
        data: The data to redact (dict, list, or primitive)
        sensitive_keys: List of key names to redact (case-insensitive)
    
    Returns:
        Redacted data with sensitive values replaced by "[REDACTED]"
    """
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            # Check if key matches any sensitive key (case-insensitive)
            is_sensitive = any(
                key.lower() == sensitive_key.lower() 
                for sensitive_key in sensitive_keys
            )
            if is_sensitive:
                result[key] = "[REDACTED]"
            else:
                result[key] = redact_sensitive_data(value, sensitive_keys)
        return result
    elif isinstance(data, list):
        return [redact_sensitive_data(item, sensitive_keys) for item in data]
    else:
        # Primitive value, return as-is
        return data
