import sqlite3
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sqlite.db")

def init_db():
    """Initializes the SQLite database schema if not already initialized."""
    logger.info(f"Initializing SQLite database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create workflow history table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS workflows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        transcript TEXT,
        intent TEXT,
        parameters TEXT,
        plan TEXT,
        tool_executed TEXT,
        tool_output TEXT,
        summary TEXT,
        status TEXT
    )
    """)
    
    conn.commit()
    conn.close()

def save_workflow_run(transcript: str, intent: str, parameters: dict, plan: list, tool_executed: str, tool_output: dict, summary: str, status: str = "Success") -> int:
    """Saves a complete workflow run to SQLite database."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
    INSERT INTO workflows (timestamp, transcript, intent, parameters, plan, tool_executed, tool_output, summary, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp,
        transcript,
        intent,
        json.dumps(parameters),
        json.dumps(plan),
        tool_executed,
        json.dumps(tool_output),
        summary,
        status
    ))
    
    run_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return run_id

def get_workflow_history(limit: int = 50) -> list:
    """Gets the history of all executed workflows, ordered by timestamp descending."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    # Configure connection to return dictionaries instead of tuples
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM workflows ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    
    history = []
    for row in rows:
        history.append({
            "id": row["id"],
            "timestamp": row["timestamp"],
            "transcript": row["transcript"],
            "intent": row["intent"],
            "parameters": json.loads(row["parameters"]) if row["parameters"] else {},
            "plan": json.loads(row["plan"]) if row["plan"] else [],
            "tool_executed": row["tool_executed"],
            "tool_output": json.loads(row["tool_output"]) if row["tool_output"] else {},
            "summary": row["summary"],
            "status": row["status"]
        })
        
    conn.close()
    return history
