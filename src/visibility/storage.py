"""
Storage module for Visibility.

Handles SQLite database operations:
- Open/create database
- Create tables and indexes
- Write events
- Query events
- Count events
"""

import sqlite3
import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path


class Storage:
    """SQLite storage backend for Visibility events."""
    
    def __init__(self, db_path: str):
        """
        Initialize storage with database path.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        
        # Ensure directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir:
            Path(db_dir).mkdir(parents=True, exist_ok=True)
        
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                level TEXT NOT NULL,
                status TEXT,
                payload TEXT NOT NULL
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_name ON events(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
        
        conn.commit()
    
    def write_event(self, event: Dict[str, Any]) -> None:
        """
        Write an event to the database.
        
        Args:
            event: Event dictionary to store
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Extract fields from event
        event_id = event["id"]
        timestamp = event["timestamp"]
        event_type = event["type"]
        name = event["name"]
        level = event["level"]
        status = event.get("status")
        
        # Store full event as JSON payload
        payload = json.dumps(event)
        
        cursor.execute(
            """
            INSERT OR REPLACE INTO events (id, timestamp, type, name, level, status, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (event_id, timestamp, event_type, name, level, status, payload)
        )
        
        conn.commit()
    
    def query(
        self,
        event_type: Optional[str] = None,
        name: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query events from the database.
        
        Args:
            event_type: Filter by event type
            name: Filter by event name
            since: Filter events after this ISO timestamp
            until: Filter events before this ISO timestamp
            limit: Maximum number of events to return
        
        Returns:
            List of event dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Build query
        query = "SELECT payload FROM events WHERE 1=1"
        params: List[Any] = []
        
        if event_type:
            query += " AND type = ?"
            params.append(event_type)
        
        if name:
            query += " AND name = ?"
            params.append(name)
        
        if since:
            query += " AND timestamp >= ?"
            params.append(since)
        
        if until:
            query += " AND timestamp <= ?"
            params.append(until)
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        
        # Parse JSON payloads
        events = []
        for row in cursor.fetchall():
            event = json.loads(row["payload"])
            events.append(event)
        
        return events
    
    def count(
        self,
        event_type: Optional[str] = None,
        name: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> int:
        """
        Count events in the database.
        
        Args:
            event_type: Filter by event type
            name: Filter by event name
            since: Filter events after this ISO timestamp
            until: Filter events before this ISO timestamp
        
        Returns:
            Number of matching events
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Build query
        query = "SELECT COUNT(*) FROM events WHERE 1=1"
        params: List[Any] = []
        
        if event_type:
            query += " AND type = ?"
            params.append(event_type)
        
        if name:
            query += " AND name = ?"
            params.append(name)
        
        if since:
            query += " AND timestamp >= ?"
            params.append(since)
        
        if until:
            query += " AND timestamp <= ?"
            params.append(until)
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        return result[0] if result else 0
    
    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
