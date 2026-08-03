"""
CLI module for Visibility.

Provides command-line interface with strict JSON output.
Supports schema, track, query, and summary commands.
"""

import argparse
import json
import sys
from typing import Dict, Any, Optional


def output_json(data: Dict[str, Any]) -> None:
    """Output data as strict JSON to stdout."""
    print(json.dumps(data))


def output_error(message: str) -> None:
    """Output error as strict JSON to stdout."""
    output_json({"ok": False, "error": message})


def output_success(data: Optional[Dict[str, Any]] = None) -> None:
    """Output success as strict JSON to stdout."""
    result = {"ok": True}
    if data:
        result.update(data)
    output_json(result)


def cmd_schema(args: argparse.Namespace) -> None:
    """Handle 'schema' command."""
    try:
        from visibility.schemas import get_openai_tool_schema, get_mcp_manifest
        
        result = {
            "openai": get_openai_tool_schema(),
            "mcp": get_mcp_manifest()
        }
        output_success(result)
    except Exception as e:
        output_error(str(e))


def cmd_track(args: argparse.Namespace) -> None:
    """Handle 'track' command."""
    try:
        from visibility import Visibility
        
        # Parse JSON input
        try:
            event_data = json.loads(args.json)
        except json.JSONDecodeError as e:
            output_error(f"Invalid JSON: {str(e)}")
            return
        
        # Create tracker
        v = Visibility()
        
        # Extract fields
        event_type = event_data.get("type", "custom")
        name = event_data.get("name", "unnamed")
        level = event_data.get("level", "info")
        status = event_data.get("status")
        duration_ms = event_data.get("duration_ms")
        request = event_data.get("request")
        error = event_data.get("error")
        llm = event_data.get("llm")
        context = event_data.get("context")
        tags = event_data.get("tags")
        
        # Track based on type
        if event_type == "request":
            event = v.track_request(
                name=name,
                method=request.get("method", "GET") if request else "GET",
                url=request.get("url", "") if request else "",
                status_code=request.get("status_code", 200) if request else 200,
                duration_ms=duration_ms,
                context=context,
                tags=tags
            )
        elif event_type == "error":
            event = v.track_error(
                name=name,
                message=error.get("message", "") if error else "Unknown error",
                error_name=error.get("name", "Error") if error else "Error",
                duration_ms=duration_ms,
                context=context,
                tags=tags
            )
        elif event_type == "llm":
            llm_data = llm or {}
            event = v.track_llm(
                name=name,
                provider=llm_data.get("provider", "openai"),
                model=llm_data.get("model", ""),
                prompt_tokens=llm_data.get("prompt_tokens", 0),
                completion_tokens=llm_data.get("completion_tokens", 0),
                duration_ms=duration_ms,
                context=context,
                tags=tags
            )
        else:
            event = v.track_custom(
                name=name,
                level=level,
                status=status,
                duration_ms=duration_ms,
                context=context,
                tags=tags
            )
        
        v.close()
        output_success({"event": event})
    
    except Exception as e:
        output_error(str(e))


def cmd_query(args: argparse.Namespace) -> None:
    """Handle 'query' command."""
    try:
        from visibility import Visibility
        
        # Create tracker
        v = Visibility()
        
        # Query events
        events = v.query(
            event_type=args.type if hasattr(args, 'type') else None,
            name=args.name if hasattr(args, 'name') else None,
            since=args.since if hasattr(args, 'since') else None,
            until=args.until if hasattr(args, 'until') else None,
            limit=args.limit if hasattr(args, 'limit') else 100
        )
        
        v.close()
        output_success({"events": events})
    
    except Exception as e:
        output_error(str(e))


def cmd_summary(args: argparse.Namespace) -> None:
    """Handle 'summary' command."""
    try:
        from visibility import Visibility
        
        # Create tracker
        v = Visibility()
        
        # Generate summary
        summary = v.summary(
            since=args.since if hasattr(args, 'since') else None,
            until=args.until if hasattr(args, 'until') else None
        )
        
        v.close()
        output_success({"summary": summary})
    
    except Exception as e:
        output_error(str(e))


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="visibility",
        description="Visibility CLI - Local-first observability for AI agents"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Schema command
    schema_parser = subparsers.add_parser("schema", help="Show OpenAI and MCP schemas")
    schema_parser.set_defaults(func=cmd_schema)
    
    # Track command
    track_parser = subparsers.add_parser("track", help="Track a new event")
    track_parser.add_argument("--json", required=True, help="JSON event data")
    track_parser.set_defaults(func=cmd_track)
    
    # Query command
    query_parser = subparsers.add_parser("query", help="Query events")
    query_parser.add_argument("--type", help="Filter by event type")
    query_parser.add_argument("--name", help="Filter by event name")
    query_parser.add_argument("--since", help="Filter events after ISO timestamp")
    query_parser.add_argument("--until", help="Filter events before ISO timestamp")
    query_parser.add_argument("--limit", type=int, default=100, help="Maximum events to return")
    query_parser.set_defaults(func=cmd_query)
    
    # Summary command
    summary_parser = subparsers.add_parser("summary", help="Generate usage summary")
    summary_parser.add_argument("--since", help="Filter events after ISO timestamp")
    summary_parser.add_argument("--until", help="Filter events before ISO timestamp")
    summary_parser.set_defaults(func=cmd_summary)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        output_error("No command specified")
        sys.exit(1)
    
    # Execute command
    args.func(args)


if __name__ == "__main__":
    main()
