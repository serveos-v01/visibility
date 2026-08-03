"""
Summary module for Visibility.

Calculates totals, token usage, estimated cost,
finds top models, recent errors, and budget status.
"""

from typing import Dict, List, Any, Optional


def calculate_summary(events: List[Dict[str, Any]], monthly_usd_limit: Optional[float] = None) -> Dict[str, Any]:
    """
    Calculate summary statistics from events.
    
    Args:
        events: List of event dictionaries
        monthly_usd_limit: Optional monthly budget limit
    
    Returns:
        Summary dictionary with totals and statistics
    """
    total_events = len(events)
    total_requests = 0
    total_errors = 0
    total_llm_calls = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0
    estimated_cost_usd = 0.0
    
    model_counts: Dict[str, int] = {}
    recent_errors: List[Dict[str, Any]] = []
    
    for event in events:
        event_type = event.get("type")
        
        if event_type == "request":
            total_requests += 1
        
        elif event_type == "error":
            total_errors += 1
            # Collect recent errors (up to 5)
            if len(recent_errors) < 5:
                error_info = {
                    "name": event.get("name"),
                    "message": event.get("error", {}).get("message") if event.get("error") else None,
                    "timestamp": event.get("timestamp")
                }
                recent_errors.append(error_info)
        
        elif event_type == "llm":
            total_llm_calls += 1
            llm_data = event.get("llm", {})
            
            prompt_tokens = llm_data.get("prompt_tokens", 0) or 0
            completion_tokens = llm_data.get("completion_tokens", 0) or 0
            event_total_tokens = prompt_tokens + completion_tokens
            
            total_prompt_tokens += prompt_tokens
            total_completion_tokens += completion_tokens
            total_tokens += event_total_tokens
            
            # Add cost if available
            event_cost = llm_data.get("estimated_cost_usd", 0.0) or 0.0
            estimated_cost_usd += event_cost
            
            # Track model usage
            model = llm_data.get("model", "unknown")
            model_counts[model] = model_counts.get(model, 0) + 1
    
    # Calculate top models
    top_models = sorted(
        [{"model": model, "count": count} for model, count in model_counts.items()],
        key=lambda x: x["count"],
        reverse=True
    )[:10]  # Top 10 models
    
    # Calculate budget status
    budget = {}
    if monthly_usd_limit is not None:
        used_usd = estimated_cost_usd
        threshold_ratio = used_usd / monthly_usd_limit if monthly_usd_limit > 0 else 0
        exceeded = used_usd >= monthly_usd_limit
        
        budget = {
            "monthly_limit_usd": monthly_usd_limit,
            "used_usd": round(used_usd, 6),
            "threshold": 0.8,
            "exceeded": exceeded
        }
    
    return {
        "total_events": total_events,
        "total_requests": total_requests,
        "total_errors": total_errors,
        "total_llm_calls": total_llm_calls,
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": round(estimated_cost_usd, 6),
        "top_models": top_models,
        "recent_errors": recent_errors,
        "budget": budget
    }
