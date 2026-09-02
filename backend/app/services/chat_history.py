import os
import sqlite3
import uuid
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

from app.config import settings

logger = logging.getLogger("docmind.chat_history")


class ChatHistoryService:
    """Service for managing chat session and message persistence in SQLite."""

    _default_db_path: Optional[str] = None

    @classmethod
    def get_db_path(cls, db_path: Optional[str] = None) -> str:
        """Resolves the database file path."""
        if db_path:
            return db_path
        if cls._default_db_path:
            return cls._default_db_path
        # Fallback to config settings default
        default_path = Path(settings.BASE_DIR) / "data" / "chat_history.db"
        return str(default_path)

    @classmethod
    def set_default_db_path(cls, db_path: str) -> None:
        """Overrides default database path (primarily used in testing)."""
        cls._default_db_path = db_path

    @classmethod
    def reset_default_db_path(cls) -> None:
        """Resets the default database path to None."""
        cls._default_db_path = None

    @classmethod
    def _get_connection(cls, db_path: Optional[str] = None) -> sqlite3.Connection:
        """Opens and configures a SQLite connection."""
        path = cls.get_db_path(db_path)
        parent_dir = os.path.dirname(path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        conn = sqlite3.connect(path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @classmethod
    def init_db(cls, db_path: Optional[str] = None) -> None:
        """Initializes database schema and indexes idempotently."""
        conn = cls._get_connection(db_path)
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        sources TEXT,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                    );
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sessions_updated_at 
                    ON sessions (updated_at DESC);
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_messages_session_id 
                    ON messages (session_id, created_at ASC);
                """)
            logger.info("Chat history database initialized successfully at %s", cls.get_db_path(db_path))
        finally:
            conn.close()

    @classmethod
    def create_session(
        cls,
        title: str = "Nova Conversa",
        session_id: Optional[str] = None,
        db_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a new chat session."""
        cls.init_db(db_path)
        s_id = session_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        conn = cls._get_connection(db_path)
        try:
            with conn:
                conn.execute(
                    "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (s_id, title.strip() or "Nova Conversa", now, now)
                )
            return {
                "id": s_id,
                "title": title.strip() or "Nova Conversa",
                "created_at": now,
                "updated_at": now
            }
        finally:
            conn.close()

    @classmethod
    def list_sessions(cls, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists all chat sessions ordered by updated_at DESC."""
        cls.init_db(db_path)
        conn = cls._get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
                for row in rows
            ]
        finally:
            conn.close()

    @classmethod
    def get_session(cls, session_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieves session metadata and full message history."""
        cls.init_db(db_path)
        conn = cls._get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, title, created_at, updated_at FROM sessions WHERE id = ?",
                (session_id,)
            )
            session_row = cursor.fetchone()
            if not session_row:
                return None

            cursor.execute(
                "SELECT id, session_id, role, content, sources, created_at FROM messages WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,)
            )
            message_rows = cursor.fetchall()

            messages = []
            for row in message_rows:
                sources_data = None
                if row["sources"]:
                    try:
                        sources_data = json.loads(row["sources"])
                    except Exception:
                        sources_data = None

                messages.append({
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "role": row["role"],
                    "content": row["content"],
                    "sources": sources_data,
                    "created_at": row["created_at"]
                })

            return {
                "id": session_row["id"],
                "title": session_row["title"],
                "created_at": session_row["created_at"],
                "updated_at": session_row["updated_at"],
                "messages": messages
            }
        finally:
            conn.close()

    @classmethod
    def add_message(
        cls,
        session_id: str,
        role: str,
        content: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        db_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Adds a message to a session and updates the session updated_at timestamp."""
        cls.init_db(db_path)
        conn = cls._get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title FROM sessions WHERE id = ?", (session_id,))
            session_row = cursor.fetchone()
            if not session_row:
                raise ValueError(f"Session '{session_id}' not found.")

            msg_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            sources_json = json.dumps(sources, ensure_ascii=False) if sources is not None else None

            with conn:
                cursor.execute(
                    """
                    INSERT INTO messages (id, session_id, role, content, sources, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (msg_id, session_id, role, content, sources_json, now)
                )

                # If first message in a default-titled session, auto-update title from user prompt
                current_title = session_row["title"]
                if current_title == "Nova Conversa" and role == "user" and content.strip():
                    first_line = content.strip().split("\n")[0].strip()
                    auto_title = (first_line[:40] + "...") if len(first_line) > 40 else first_line
                    cursor.execute(
                        "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                        (auto_title, now, session_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE sessions SET updated_at = ? WHERE id = ?",
                        (now, session_id)
                    )

            return {
                "id": msg_id,
                "session_id": session_id,
                "role": role,
                "content": content,
                "sources": sources,
                "created_at": now
            }
        finally:
            conn.close()

    @classmethod
    def delete_session(cls, session_id: str, db_path: Optional[str] = None) -> bool:
        """Deletes a session and associated messages."""
        cls.init_db(db_path)
        conn = cls._get_connection(db_path)
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
                cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
                return cursor.rowcount > 0
        finally:
            conn.close()

    @classmethod
    def update_session_title(
        cls,
        session_id: str,
        title: str,
        db_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Updates the title of an existing session."""
        cls.init_db(db_path)
        conn = cls._get_connection(db_path)
        try:
            now = datetime.now(timezone.utc).isoformat()
            clean_title = title.strip() or "Conversa sem título"
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                    (clean_title, now, session_id)
                )
                if cursor.rowcount == 0:
                    return None
                
                cursor.execute("SELECT id, title, created_at, updated_at FROM sessions WHERE id = ?", (session_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                return {
                    "id": row["id"],
                    "title": row["title"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
        finally:
            conn.close()

    @classmethod
    def clear_all(cls, db_path: Optional[str] = None) -> None:
        """Clears all sessions and messages (used in testing/maintenance)."""
        cls.init_db(db_path)
        conn = cls._get_connection(db_path)
        try:
            with conn:
                conn.execute("DELETE FROM messages;")
                conn.execute("DELETE FROM sessions;")
        finally:
            conn.close()


# Module-level convenience functions matching Interface Contracts
init_db = ChatHistoryService.init_db
create_session = ChatHistoryService.create_session
list_sessions = ChatHistoryService.list_sessions
get_session = ChatHistoryService.get_session
add_message = ChatHistoryService.add_message
delete_session = ChatHistoryService.delete_session
update_session_title = ChatHistoryService.update_session_title
clear_all = ChatHistoryService.clear_all
chat_history_service = ChatHistoryService()
