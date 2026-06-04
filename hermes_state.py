#!/usr/bin/env python3
"""
SQLite State Store for Hermes Agent.

Provides persistent session storage with FTS5 full-text search, replacing
the per-session JSONL file approach. Stores session metadata, full message
history, and model configuration for CLI and gateway sessions.

Key design decisions:
- WAL mode for concurrent readers + one writer (gateway multi-platform)
- FTS5 virtual table for fast text search across all session messages
- Compression-triggered session splitting via parent_session_id chains
- Batch runner and RL trajectories are NOT stored here (separate systems)
- Session source tagging ('cli', 'telegram', 'discord', etc.) for filtering
"""

import json
import hashlib
import os
import re
import sqlite3
import threading
import time
from pathlib import Path
from hermes_constants import get_hermes_home
from typing import Dict, Any, List, Optional


DEFAULT_DB_PATH = get_hermes_home() / "state.db"

SCHEMA_VERSION = 7

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    user_id TEXT,
    model TEXT,
    model_config TEXT,
    system_prompt TEXT,
    parent_session_id TEXT,
    started_at REAL NOT NULL,
    ended_at REAL,
    end_reason TEXT,
    message_count INTEGER DEFAULT 0,
    tool_call_count INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_write_tokens INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    billing_provider TEXT,
    billing_base_url TEXT,
    billing_mode TEXT,
    estimated_cost_usd REAL,
    actual_cost_usd REAL,
    cost_status TEXT,
    cost_source TEXT,
    pricing_version TEXT,
    title TEXT,
    FOREIGN KEY (parent_session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,
    content TEXT,
    tool_call_id TEXT,
    tool_calls TEXT,
    tool_name TEXT,
    timestamp REAL NOT NULL,
    token_count INTEGER,
    finish_reason TEXT,
    reasoning TEXT,
    reasoning_details TEXT,
    codex_reasoning_items TEXT,
    replay_content TEXT,
    search_content TEXT,
    content_sha256 TEXT,
    content_artifacted INTEGER DEFAULT 0,
    content_artifact_kind TEXT,
    content_byte_count INTEGER
);

CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sha256 TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    mime_type TEXT,
    byte_count INTEGER NOT NULL,
    content BLOB NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS message_artifacts (
    message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    artifact_id INTEGER NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL DEFAULT 'raw_content',
    created_at REAL NOT NULL,
    PRIMARY KEY (message_id, artifact_id, purpose)
);

CREATE TABLE IF NOT EXISTS prompt_blocks (
    sha256 TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    name TEXT,
    content TEXT NOT NULL,
    token_count INTEGER,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS session_prompt_blocks (
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    block_sha256 TEXT NOT NULL REFERENCES prompt_blocks(sha256) ON DELETE CASCADE,
    block_order INTEGER NOT NULL,
    block_role TEXT NOT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY (session_id, block_sha256, block_order)
);

CREATE INDEX IF NOT EXISTS idx_sessions_source ON sessions(source);
CREATE INDEX IF NOT EXISTS idx_sessions_parent ON sessions(parent_session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_artifacts_sha ON artifacts(sha256);
CREATE INDEX IF NOT EXISTS idx_message_artifacts_message ON message_artifacts(message_id);
CREATE INDEX IF NOT EXISTS idx_session_prompt_blocks_session ON session_prompt_blocks(session_id, block_order);
"""

FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    content=messages,
    content_rowid=id
);

CREATE TRIGGER IF NOT EXISTS messages_fts_insert AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content) VALUES (new.id, COALESCE(new.search_content, new.content));
END;

CREATE TRIGGER IF NOT EXISTS messages_fts_delete AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, COALESCE(old.search_content, old.content));
END;

CREATE TRIGGER IF NOT EXISTS messages_fts_update AFTER UPDATE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, COALESCE(old.search_content, old.content));
    INSERT INTO messages_fts(rowid, content) VALUES (new.id, COALESCE(new.search_content, new.content));
END;
"""


class SessionDB:
    """
    SQLite-backed session storage with FTS5 search.

    Thread-safe for the common gateway pattern (multiple reader threads,
    single writer via WAL mode). Each method opens its own cursor.
    """

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            # 30s gives the WAL writer (CLI or gateway) time to finish a batch
            # flush before the concurrent reader/writer gives up.  10s was too
            # short when the CLI is doing frequent memory flushes.
            timeout=30.0,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

        self._init_schema()

    def _init_schema(self):
        """Create tables and FTS if they don't exist, run migrations."""
        cursor = self._conn.cursor()

        cursor.executescript(SCHEMA_SQL)

        # Check schema version and run migrations
        cursor.execute("SELECT version FROM schema_version LIMIT 1")
        row = cursor.fetchone()
        if row is None:
            cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        else:
            current_version = row["version"] if isinstance(row, sqlite3.Row) else row[0]
            if current_version < 2:
                # v2: add finish_reason column to messages
                try:
                    cursor.execute("ALTER TABLE messages ADD COLUMN finish_reason TEXT")
                except sqlite3.OperationalError:
                    pass  # Column already exists
                cursor.execute("UPDATE schema_version SET version = 2")
            if current_version < 3:
                # v3: add title column to sessions
                try:
                    cursor.execute("ALTER TABLE sessions ADD COLUMN title TEXT")
                except sqlite3.OperationalError:
                    pass  # Column already exists
                cursor.execute("UPDATE schema_version SET version = 3")
            if current_version < 4:
                # v4: add unique index on title (NULLs allowed, only non-NULL must be unique)
                try:
                    cursor.execute(
                        "CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_title_unique "
                        "ON sessions(title) WHERE title IS NOT NULL"
                    )
                except sqlite3.OperationalError:
                    pass  # Index already exists
                cursor.execute("UPDATE schema_version SET version = 4")
            if current_version < 5:
                new_columns = [
                    ("cache_read_tokens", "INTEGER DEFAULT 0"),
                    ("cache_write_tokens", "INTEGER DEFAULT 0"),
                    ("reasoning_tokens", "INTEGER DEFAULT 0"),
                    ("billing_provider", "TEXT"),
                    ("billing_base_url", "TEXT"),
                    ("billing_mode", "TEXT"),
                    ("estimated_cost_usd", "REAL"),
                    ("actual_cost_usd", "REAL"),
                    ("cost_status", "TEXT"),
                    ("cost_source", "TEXT"),
                    ("pricing_version", "TEXT"),
                ]
                for name, column_type in new_columns:
                    try:
                        # name and column_type come from the hardcoded tuple above,
                        # not user input. Double-quote identifier escaping is applied
                        # as defense-in-depth; SQLite DDL cannot be parameterized.
                        safe_name = name.replace('"', '""')
                        cursor.execute(f'ALTER TABLE sessions ADD COLUMN "{safe_name}" {column_type}')
                    except sqlite3.OperationalError:
                        pass
                cursor.execute("UPDATE schema_version SET version = 5")
            if current_version < 6:
                # v6: add reasoning columns to messages table — preserves assistant
                # reasoning text and structured reasoning_details across gateway
                # session turns.  Without these, reasoning chains are lost on
                # session reload, breaking multi-turn reasoning continuity for
                # providers that replay reasoning (OpenRouter, OpenAI, Nous).
                for col_name, col_type in [
                    ("reasoning", "TEXT"),
                    ("reasoning_details", "TEXT"),
                    ("codex_reasoning_items", "TEXT"),
                ]:
                    try:
                        safe = col_name.replace('"', '""')
                        cursor.execute(
                            f'ALTER TABLE messages ADD COLUMN "{safe}" {col_type}'
                        )
                    except sqlite3.OperationalError:
                        pass  # Column already exists
                cursor.execute("UPDATE schema_version SET version = 6")
            if current_version < 7:
                # v7: artifact-backed replay. Exact raw blobs live in artifacts,
                # messages carry bounded replay/search projections, and prompt
                # blocks are content-addressed without changing sessions.system_prompt.
                for col_name, col_type in [
                    ("replay_content", "TEXT"),
                    ("search_content", "TEXT"),
                    ("content_sha256", "TEXT"),
                    ("content_artifacted", "INTEGER DEFAULT 0"),
                    ("content_artifact_kind", "TEXT"),
                    ("content_byte_count", "INTEGER"),
                ]:
                    try:
                        safe = col_name.replace('"', '""')
                        cursor.execute(
                            f'ALTER TABLE messages ADD COLUMN "{safe}" {col_type}'
                        )
                    except sqlite3.OperationalError:
                        pass

                cursor.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS artifacts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sha256 TEXT NOT NULL UNIQUE,
                        kind TEXT NOT NULL,
                        mime_type TEXT,
                        byte_count INTEGER NOT NULL,
                        content BLOB NOT NULL,
                        created_at REAL NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS message_artifacts (
                        message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
                        artifact_id INTEGER NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
                        purpose TEXT NOT NULL DEFAULT 'raw_content',
                        created_at REAL NOT NULL,
                        PRIMARY KEY (message_id, artifact_id, purpose)
                    );
                    CREATE TABLE IF NOT EXISTS prompt_blocks (
                        sha256 TEXT PRIMARY KEY,
                        kind TEXT NOT NULL,
                        name TEXT,
                        content TEXT NOT NULL,
                        token_count INTEGER,
                        created_at REAL NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS session_prompt_blocks (
                        session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                        block_sha256 TEXT NOT NULL REFERENCES prompt_blocks(sha256) ON DELETE CASCADE,
                        block_order INTEGER NOT NULL,
                        block_role TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        PRIMARY KEY (session_id, block_sha256, block_order)
                    );
                    CREATE INDEX IF NOT EXISTS idx_messages_content_sha ON messages(content_sha256);
                    CREATE INDEX IF NOT EXISTS idx_artifacts_sha ON artifacts(sha256);
                    CREATE INDEX IF NOT EXISTS idx_message_artifacts_message ON message_artifacts(message_id);
                    CREATE INDEX IF NOT EXISTS idx_session_prompt_blocks_session
                        ON session_prompt_blocks(session_id, block_order);
                    """
                )
                cursor.execute(
                    """UPDATE messages
                       SET replay_content = COALESCE(replay_content, content),
                           search_content = COALESCE(search_content, content),
                           content_artifacted = COALESCE(content_artifacted, 0),
                           content_byte_count = COALESCE(content_byte_count, length(COALESCE(content, '')))
                       WHERE replay_content IS NULL
                          OR search_content IS NULL
                          OR content_byte_count IS NULL"""
                )
                cursor.execute("DROP TRIGGER IF EXISTS messages_fts_insert")
                cursor.execute("DROP TRIGGER IF EXISTS messages_fts_delete")
                cursor.execute("DROP TRIGGER IF EXISTS messages_fts_update")
                cursor.executescript(FTS_SQL)
                try:
                    cursor.execute("INSERT INTO messages_fts(messages_fts) VALUES('rebuild')")
                except sqlite3.OperationalError:
                    pass
                cursor.execute("UPDATE schema_version SET version = 7")

        # Unique title index — always ensure it exists (safe to run after migrations
        # since the title column is guaranteed to exist at this point)
        try:
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_title_unique "
                "ON sessions(title) WHERE title IS NOT NULL"
            )
        except sqlite3.OperationalError:
            pass  # Index already exists

        try:
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_content_sha "
                "ON messages(content_sha256)"
            )
        except sqlite3.OperationalError:
            pass

        # FTS5 setup (separate because CREATE VIRTUAL TABLE can't be in executescript with IF NOT EXISTS reliably)
        try:
            cursor.execute("SELECT * FROM messages_fts LIMIT 0")
        except sqlite3.OperationalError:
            cursor.executescript(FTS_SQL)

        self._conn.commit()

    def close(self):
        """Close the database connection."""
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None

    # =========================================================================
    # Artifact and prompt-block helpers
    # =========================================================================

    LARGE_MESSAGE_ARTIFACT_CHARS = 4_000
    LARGE_TOOL_ARTIFACT_CHARS = 4_000
    EXACT_RECENT_REPLAY_MESSAGES = 8

    @staticmethod
    def _sha256_text(text: str) -> str:
        return hashlib.sha256((text or "").encode("utf-8")).hexdigest()

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        if not text:
            return 0
        return max(1, (len(text) + 3) // 4)

    @staticmethod
    def _artifact_kind(role: str, tool_name: str = None) -> str:
        tool = (tool_name or "").lower()
        if role == "tool":
            if "terminal" in tool or "shell" in tool or "bash" in tool:
                return "terminal_output"
            if "file" in tool or "read" in tool or "search" in tool or "patch" in tool:
                return "file_tool_output"
            if "web" in tool or "browser" in tool:
                return "web_tool_output"
            return "tool_output"
        return "message_content"

    def _should_artifactize(self, role: str, content: str, tool_name: str = None) -> bool:
        if not content:
            return False
        if role == "tool" and len(content) > self.LARGE_TOOL_ARTIFACT_CHARS:
            return True
        return len(content) > self.LARGE_MESSAGE_ARTIFACT_CHARS

    @staticmethod
    def _head_tail(text: str, head_chars: int = 1200, tail_chars: int = 1200) -> tuple[str, str]:
        if len(text) <= head_chars + tail_chars:
            return text, ""
        return text[:head_chars], text[-tail_chars:]

    _MESSAGE_EVIDENCE_PATTERNS = (
        ("paperclip_agent", re.compile(r"(?im)^\s*you are ([^\r\n]+?) running inside paperclip(?: through hermes)?\.?")),
        ("prompt_class", re.compile(r"(?im)^\s*(?:prompt\s*class|promptClass|prompt_class)\s*[:=]\s*([^\r\n]+)")),
        ("cwd", re.compile(r"(?im)^\s*(?:working directory|cwd)\s*[:=]\s*([^\r\n]+)")),
        ("paperclip_run", re.compile(r"(?im)^\s*paperclip run\s*[:=]\s*([^\r\n]+)")),
        ("command", re.compile(r"(?im)^\s*(?:command|last command)\s*[:=]\s*([^\r\n]+)")),
        ("branch", re.compile(r"(?im)^\s*(?:branch|git branch)\s*[:=]\s*([^\r\n]+)")),
        ("task", re.compile(r"(?im)^\s*(?:task key|task|issue)\s*[:=]\s*([^\r\n]+)")),
        ("blocker", re.compile(r"(?im)^\s*(?:final blocker|blocker|error)\s*[:=]\s*([^\r\n]+)")),
        ("receipt_path", re.compile(r"(?im)^\s*(?:receipt path|receipt_path|receipt)\s*[:=]\s*([^\s\r\n]+)")),
        ("context_pack", re.compile(r"(?im)^\s*(?:context pack|pack manifest|manifest path)\s*[:=]\s*([^\r\n]+)")),
    )
    _MESSAGE_JSON_EVIDENCE_PATTERN = re.compile(
        r'"(promptClass|prompt_class|cwd|branch|taskKey|issueKey|receiptPath|'
        r'manifestPath|packPath|packSha|manifestSha|freshness|selectedProfile)"\s*:\s*"([^"]+)"'
    )
    _MESSAGE_SIGNATURE_EXCLUDED_LABELS = {"paperclip_run"}

    @classmethod
    def _message_evidence_slices(
        cls,
        text: str,
        *,
        max_slices: int = 5,
        value_chars: int = 140,
    ) -> list[str]:
        slices: list[str] = []
        seen: set[str] = set()

        def add(label: str, value: str) -> None:
            if len(slices) >= max_slices:
                return
            normalized = re.sub(r"\s+", " ", value or "").strip()
            if not normalized:
                return
            if len(normalized) > value_chars:
                normalized = normalized[: value_chars - 1].rstrip() + "..."
            line = f"{label}: {normalized}"
            key = line.lower()
            if key in seen:
                return
            seen.add(key)
            slices.append(line)

        for label, pattern in cls._MESSAGE_EVIDENCE_PATTERNS:
            match = pattern.search(text or "")
            if match:
                add(label, match.group(1))
        for match in cls._MESSAGE_JSON_EVIDENCE_PATTERN.finditer(text or ""):
            add(match.group(1), match.group(2))
        return slices

    @classmethod
    def _message_evidence_signature(cls, text: str) -> str:
        slices = cls._message_evidence_slices(text, max_slices=12, value_chars=240)
        signature_slices = [
            line for line in slices
            if line.split(":", 1)[0] not in cls._MESSAGE_SIGNATURE_EXCLUDED_LABELS
        ]
        if len(signature_slices) < 2:
            return ""
        signature = "\n".join(line.lower() for line in signature_slices)
        return hashlib.sha256(signature.encode("utf-8")).hexdigest()

    def _build_replay_content(self, *, raw: str, sha256: str, kind: str) -> str:
        if kind == "message_content":
            evidence = self._message_evidence_slices(raw)
            head, tail = self._head_tail(raw, head_chars=180, tail_chars=180)
        else:
            evidence = []
            head, tail = self._head_tail(raw)
        lines = [
            "[Hermes artifact-backed replay]",
            f"kind: {kind}",
            f"sha256: {sha256}",
            f"chars: {len(raw)}",
            f"estimated_tokens: {self._estimate_tokens(raw)}",
        ]
        if evidence:
            lines.extend(["", "evidence_slices:"])
            lines.extend(f"- {line}" for line in evidence)
        lines.extend(["", "head:", head])
        if tail:
            lines.extend(["", "tail:", tail])
        lines.extend([
            "",
            "Full exact content is stored as an audit artifact and indexed through search_content.",
        ])
        return "\n".join(lines)

    @staticmethod
    def _build_duplicate_replay_content(*, sha256: str, kind: str, chars: int | None) -> str:
        lines = [
            "[Hermes artifact-backed replay]",
            f"kind: {kind}",
            f"sha256: {sha256}",
        ]
        if chars is not None:
            lines.append(f"chars: {chars}")
        lines.extend([
            "duplicate_of_prior_artifact: true",
            "Full exact content is stored as an audit artifact and indexed through search_content.",
        ])
        return "\n".join(lines)

    @staticmethod
    def _build_related_replay_content(
        *,
        sha256: str,
        kind: str,
        chars: int | None,
        signature_sha256: str,
        prior_sha256: str,
    ) -> str:
        lines = [
            "[Hermes artifact-backed replay]",
            f"kind: {kind}",
            f"sha256: {sha256}",
        ]
        if chars is not None:
            lines.append(f"chars: {chars}")
        lines.extend([
            "same_evidence_signature_as_prior: true",
            f"signature_sha256: {signature_sha256}",
            f"prior_artifact_sha256: {prior_sha256}",
            "Full exact content is stored as an audit artifact and indexed through search_content.",
        ])
        return "\n".join(lines)

    def _artifactize_existing_message_locked(self, row: sqlite3.Row) -> tuple[str, str, str, str]:
        """Move a legacy large message into the artifact store.

        v7 migration preserves legacy rows byte-for-byte. This lazy path lets
        old resumed sessions benefit from bounded replay without a destructive
        rewrite job or loss of exact audit content.
        """
        raw = row["content"] or ""
        kind = self._artifact_kind(row["role"], row["tool_name"])
        sha = self._sha256_text(raw)
        replay = self._build_replay_content(raw=raw, sha256=sha, kind=kind)
        artifact_id = self._store_artifact_locked(sha256=sha, kind=kind, content=raw)
        self._conn.execute(
            """UPDATE messages
               SET content = ?,
                   replay_content = ?,
                   search_content = ?,
                   content_sha256 = ?,
                   content_artifacted = 1,
                   content_artifact_kind = ?,
                   content_byte_count = ?
               WHERE id = ?""",
            (
                replay,
                replay,
                raw,
                sha,
                kind,
                len(raw.encode("utf-8")),
                row["id"],
            ),
        )
        self._conn.execute(
            """INSERT OR IGNORE INTO message_artifacts
               (message_id, artifact_id, purpose, created_at)
               VALUES (?, ?, 'raw_content', ?)""",
            (row["id"], artifact_id, time.time()),
        )
        self._conn.commit()
        return raw, replay, sha, kind

    def _store_artifact_locked(
        self,
        *,
        sha256: str,
        kind: str,
        content: str,
        mime_type: str = "text/plain; charset=utf-8",
    ) -> int:
        content_bytes = content.encode("utf-8")
        self._conn.execute(
            """INSERT OR IGNORE INTO artifacts
               (sha256, kind, mime_type, byte_count, content, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (sha256, kind, mime_type, len(content_bytes), content_bytes, time.time()),
        )
        cursor = self._conn.execute(
            "SELECT id FROM artifacts WHERE sha256 = ?",
            (sha256,),
        )
        row = cursor.fetchone()
        if not row:
            raise RuntimeError("Failed to store message artifact")
        return int(row["id"])

    def _load_artifact_content_locked(self, message_id: int) -> Optional[str]:
        cursor = self._conn.execute(
            """SELECT a.content
               FROM message_artifacts ma
               JOIN artifacts a ON a.id = ma.artifact_id
               WHERE ma.message_id = ? AND ma.purpose = 'raw_content'
               ORDER BY ma.created_at DESC
               LIMIT 1""",
            (message_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        blob = row["content"]
        if isinstance(blob, bytes):
            return blob.decode("utf-8", errors="replace")
        return str(blob)

    def _store_prompt_block_locked(
        self,
        *,
        session_id: str,
        content: str,
        kind: str = "system_prompt",
        name: str = None,
        block_order: int = 0,
        block_role: str = "system",
    ) -> str:
        sha = self._sha256_text(content)
        self._conn.execute(
            """INSERT OR IGNORE INTO prompt_blocks
               (sha256, kind, name, content, token_count, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (sha, kind, name, content, self._estimate_tokens(content), time.time()),
        )
        self._conn.execute(
            """INSERT OR IGNORE INTO session_prompt_blocks
               (session_id, block_sha256, block_order, block_role, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, sha, block_order, block_role, time.time()),
        )
        return sha

    # =========================================================================
    # Session lifecycle
    # =========================================================================

    def create_session(
        self,
        session_id: str,
        source: str,
        model: str = None,
        model_config: Dict[str, Any] = None,
        system_prompt: str = None,
        user_id: str = None,
        parent_session_id: str = None,
    ) -> str:
        """Create a new session record. Returns the session_id."""
        with self._lock:
            self._conn.execute(
                """INSERT OR IGNORE INTO sessions (id, source, user_id, model, model_config,
                   system_prompt, parent_session_id, started_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    source,
                    user_id,
                    model,
                    json.dumps(model_config) if model_config else None,
                    system_prompt,
                    parent_session_id,
                    time.time(),
                ),
            )
            if system_prompt:
                self._store_prompt_block_locked(
                    session_id=session_id,
                    content=system_prompt,
                    kind="system_prompt",
                    name="sessions.system_prompt",
                    block_order=0,
                    block_role="system",
                )
            self._conn.commit()
        return session_id

    def end_session(self, session_id: str, end_reason: str) -> None:
        """Mark a session as ended."""
        with self._lock:
            self._conn.execute(
                "UPDATE sessions SET ended_at = ?, end_reason = ? WHERE id = ?",
                (time.time(), end_reason, session_id),
            )
            self._conn.commit()

    def update_system_prompt(self, session_id: str, system_prompt: str) -> None:
        """Store the full assembled system prompt snapshot."""
        with self._lock:
            self._conn.execute(
                "UPDATE sessions SET system_prompt = ? WHERE id = ?",
                (system_prompt, session_id),
            )
            if system_prompt:
                self._store_prompt_block_locked(
                    session_id=session_id,
                    content=system_prompt,
                    kind="system_prompt",
                    name="sessions.system_prompt",
                    block_order=0,
                    block_role="system",
                )
            self._conn.commit()

    def update_token_counts(
        self,
        session_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        model: str = None,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
        reasoning_tokens: int = 0,
        estimated_cost_usd: Optional[float] = None,
        actual_cost_usd: Optional[float] = None,
        cost_status: Optional[str] = None,
        cost_source: Optional[str] = None,
        pricing_version: Optional[str] = None,
        billing_provider: Optional[str] = None,
        billing_base_url: Optional[str] = None,
        billing_mode: Optional[str] = None,
    ) -> None:
        """Increment token counters and backfill model if not already set."""
        with self._lock:
            self._conn.execute(
                """UPDATE sessions SET
                   input_tokens = input_tokens + ?,
                   output_tokens = output_tokens + ?,
                   cache_read_tokens = cache_read_tokens + ?,
                   cache_write_tokens = cache_write_tokens + ?,
                   reasoning_tokens = reasoning_tokens + ?,
                   estimated_cost_usd = COALESCE(estimated_cost_usd, 0) + COALESCE(?, 0),
                   actual_cost_usd = CASE
                       WHEN ? IS NULL THEN actual_cost_usd
                       ELSE COALESCE(actual_cost_usd, 0) + ?
                   END,
                   cost_status = COALESCE(?, cost_status),
                   cost_source = COALESCE(?, cost_source),
                   pricing_version = COALESCE(?, pricing_version),
                   billing_provider = COALESCE(billing_provider, ?),
                   billing_base_url = COALESCE(billing_base_url, ?),
                   billing_mode = COALESCE(billing_mode, ?),
                   model = COALESCE(model, ?)
                   WHERE id = ?""",
                (
                    input_tokens,
                    output_tokens,
                    cache_read_tokens,
                    cache_write_tokens,
                    reasoning_tokens,
                    estimated_cost_usd,
                    actual_cost_usd,
                    actual_cost_usd,
                    cost_status,
                    cost_source,
                    pricing_version,
                    billing_provider,
                    billing_base_url,
                    billing_mode,
                    model,
                    session_id,
                ),
            )
            self._conn.commit()

    def ensure_session(
        self,
        session_id: str,
        source: str = "unknown",
        model: str = None,
    ) -> None:
        """Ensure a session row exists, creating it with minimal metadata if absent.

        Used by _flush_messages_to_session_db to recover from a failed
        create_session() call (e.g. transient SQLite lock at agent startup).
        INSERT OR IGNORE is safe to call even when the row already exists.
        """
        with self._lock:
            self._conn.execute(
                """INSERT OR IGNORE INTO sessions
                   (id, source, model, started_at)
                   VALUES (?, ?, ?, ?)""",
                (session_id, source, model, time.time()),
            )
            self._conn.commit()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by ID."""
        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            row = cursor.fetchone()
        return dict(row) if row else None

    def resolve_session_id(self, session_id_or_prefix: str) -> Optional[str]:
        """Resolve an exact or uniquely prefixed session ID to the full ID.

        Returns the exact ID when it exists. Otherwise treats the input as a
        prefix and returns the single matching session ID if the prefix is
        unambiguous. Returns None for no matches or ambiguous prefixes.
        """
        exact = self.get_session(session_id_or_prefix)
        if exact:
            return exact["id"]

        escaped = (
            session_id_or_prefix
            .replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        with self._lock:
            cursor = self._conn.execute(
                "SELECT id FROM sessions WHERE id LIKE ? ESCAPE '\\' ORDER BY started_at DESC LIMIT 2",
                (f"{escaped}%",),
            )
            matches = [row["id"] for row in cursor.fetchall()]
        if len(matches) == 1:
            return matches[0]
        return None

    # Maximum length for session titles
    MAX_TITLE_LENGTH = 100

    @staticmethod
    def sanitize_title(title: Optional[str]) -> Optional[str]:
        """Validate and sanitize a session title.

        - Strips leading/trailing whitespace
        - Removes ASCII control characters (0x00-0x1F, 0x7F) and problematic
          Unicode control chars (zero-width, RTL/LTR overrides, etc.)
        - Collapses internal whitespace runs to single spaces
        - Normalizes empty/whitespace-only strings to None
        - Enforces MAX_TITLE_LENGTH

        Returns the cleaned title string or None.
        Raises ValueError if the title exceeds MAX_TITLE_LENGTH after cleaning.
        """
        if not title:
            return None

        # Remove ASCII control characters (0x00-0x1F, 0x7F) but keep
        # whitespace chars (\t=0x09, \n=0x0A, \r=0x0D) so they can be
        # normalized to spaces by the whitespace collapsing step below
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', title)

        # Remove problematic Unicode control characters:
        # - Zero-width chars (U+200B-U+200F, U+FEFF)
        # - Directional overrides (U+202A-U+202E, U+2066-U+2069)
        # - Object replacement (U+FFFC), interlinear annotation (U+FFF9-U+FFFB)
        cleaned = re.sub(
            r'[\u200b-\u200f\u2028-\u202e\u2060-\u2069\ufeff\ufffc\ufff9-\ufffb]',
            '', cleaned,
        )

        # Collapse internal whitespace runs and strip
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        if not cleaned:
            return None

        if len(cleaned) > SessionDB.MAX_TITLE_LENGTH:
            raise ValueError(
                f"Title too long ({len(cleaned)} chars, max {SessionDB.MAX_TITLE_LENGTH})"
            )

        return cleaned

    def set_session_title(self, session_id: str, title: str) -> bool:
        """Set or update a session's title.

        Returns True if session was found and title was set.
        Raises ValueError if title is already in use by another session,
        or if the title fails validation (too long, invalid characters).
        Empty/whitespace-only strings are normalized to None (clearing the title).
        """
        title = self.sanitize_title(title)
        with self._lock:
            if title:
                # Check uniqueness (allow the same session to keep its own title)
                cursor = self._conn.execute(
                    "SELECT id FROM sessions WHERE title = ? AND id != ?",
                    (title, session_id),
                )
                conflict = cursor.fetchone()
                if conflict:
                    raise ValueError(
                        f"Title '{title}' is already in use by session {conflict['id']}"
                    )
            cursor = self._conn.execute(
                "UPDATE sessions SET title = ? WHERE id = ?",
                (title, session_id),
            )
            self._conn.commit()
            rowcount = cursor.rowcount
        return rowcount > 0

    def get_session_title(self, session_id: str) -> Optional[str]:
        """Get the title for a session, or None."""
        with self._lock:
            cursor = self._conn.execute(
                "SELECT title FROM sessions WHERE id = ?", (session_id,)
            )
            row = cursor.fetchone()
        return row["title"] if row else None

    def get_session_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Look up a session by exact title. Returns session dict or None."""
        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM sessions WHERE title = ?", (title,)
            )
            row = cursor.fetchone()
        return dict(row) if row else None

    def resolve_session_by_title(self, title: str) -> Optional[str]:
        """Resolve a title to a session ID, preferring the latest in a lineage.

        If the exact title exists, returns that session's ID.
        If not, searches for "title #N" variants and returns the latest one.
        If the exact title exists AND numbered variants exist, returns the
        latest numbered variant (the most recent continuation).
        """
        # First try exact match
        exact = self.get_session_by_title(title)

        # Also search for numbered variants: "title #2", "title #3", etc.
        # Escape SQL LIKE wildcards (%, _) in the title to prevent false matches
        escaped = title.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        with self._lock:
            cursor = self._conn.execute(
                "SELECT id, title, started_at FROM sessions "
                "WHERE title LIKE ? ESCAPE '\\' ORDER BY started_at DESC",
                (f"{escaped} #%",),
            )
            numbered = cursor.fetchall()

        if numbered:
            # Return the most recent numbered variant
            return numbered[0]["id"]
        elif exact:
            return exact["id"]
        return None

    def get_next_title_in_lineage(self, base_title: str) -> str:
        """Generate the next title in a lineage (e.g., "my session" → "my session #2").

        Strips any existing " #N" suffix to find the base name, then finds
        the highest existing number and increments.
        """
        # Strip existing #N suffix to find the true base
        match = re.match(r'^(.*?) #(\d+)$', base_title)
        if match:
            base = match.group(1)
        else:
            base = base_title

        # Find all existing numbered variants
        # Escape SQL LIKE wildcards (%, _) in the base to prevent false matches
        escaped = base.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        with self._lock:
            cursor = self._conn.execute(
                "SELECT title FROM sessions WHERE title = ? OR title LIKE ? ESCAPE '\\'",
                (base, f"{escaped} #%"),
            )
            existing = [row["title"] for row in cursor.fetchall()]

        if not existing:
            return base  # No conflict, use the base name as-is

        # Find the highest number
        max_num = 1  # The unnumbered original counts as #1
        for t in existing:
            m = re.match(r'^.* #(\d+)$', t)
            if m:
                max_num = max(max_num, int(m.group(1)))

        return f"{base} #{max_num + 1}"

    def list_sessions_rich(
        self,
        source: str = None,
        exclude_sources: List[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List sessions with preview (first user message) and last active timestamp.

        Returns dicts with keys: id, source, model, title, started_at, ended_at,
        message_count, preview (first 60 chars of first user message),
        last_active (timestamp of last message).

        Uses a single query with correlated subqueries instead of N+2 queries.
        """
        where_clauses = []
        params = []

        if source:
            where_clauses.append("s.source = ?")
            params.append(source)
        if exclude_sources:
            placeholders = ",".join("?" for _ in exclude_sources)
            where_clauses.append(f"s.source NOT IN ({placeholders})")
            params.extend(exclude_sources)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"""
            SELECT s.*,
                COALESCE(
                    (SELECT SUBSTR(REPLACE(REPLACE(m.content, X'0A', ' '), X'0D', ' '), 1, 63)
                     FROM messages m
                     WHERE m.session_id = s.id AND m.role = 'user' AND m.content IS NOT NULL
                     ORDER BY m.timestamp, m.id LIMIT 1),
                    ''
                ) AS _preview_raw,
                COALESCE(
                    (SELECT MAX(m2.timestamp) FROM messages m2 WHERE m2.session_id = s.id),
                    s.started_at
                ) AS last_active
            FROM sessions s
            {where_sql}
            ORDER BY s.started_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        with self._lock:
            cursor = self._conn.execute(query, params)
            rows = cursor.fetchall()
        sessions = []
        for row in rows:
            s = dict(row)
            # Build the preview from the raw substring
            raw = s.pop("_preview_raw", "").strip()
            if raw:
                text = raw[:60]
                s["preview"] = text + ("..." if len(raw) > 60 else "")
            else:
                s["preview"] = ""
            sessions.append(s)

        return sessions

    # =========================================================================
    # Message storage
    # =========================================================================

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str = None,
        tool_name: str = None,
        tool_calls: Any = None,
        tool_call_id: str = None,
        token_count: int = None,
        finish_reason: str = None,
        reasoning: str = None,
        reasoning_details: Any = None,
        codex_reasoning_items: Any = None,
    ) -> int:
        """
        Append a message to a session. Returns the message row ID.

        Also increments the session's message_count (and tool_call_count
        if role is 'tool' or tool_calls is present).
        """
        with self._lock:
            raw_content = content
            content_sha = self._sha256_text(raw_content) if raw_content is not None else None
            content_byte_count = (
                len(raw_content.encode("utf-8")) if raw_content is not None else None
            )
            artifact_kind = (
                self._artifact_kind(role, tool_name)
                if raw_content is not None and self._should_artifactize(role, raw_content, tool_name)
                else None
            )
            artifact_id = None
            content_artifacted = 1 if artifact_kind else 0
            replay_content = raw_content
            search_content = raw_content
            stored_content = raw_content
            if artifact_kind and raw_content is not None and content_sha is not None:
                artifact_id = self._store_artifact_locked(
                    sha256=content_sha,
                    kind=artifact_kind,
                    content=raw_content,
                )
                replay_content = self._build_replay_content(
                    raw=raw_content,
                    sha256=content_sha,
                    kind=artifact_kind,
                )
                stored_content = replay_content

            # Serialize structured fields to JSON for storage
            reasoning_details_json = (
                json.dumps(reasoning_details)
                if reasoning_details else None
            )
            codex_items_json = (
                json.dumps(codex_reasoning_items)
                if codex_reasoning_items else None
            )
            cursor = self._conn.execute(
                """INSERT INTO messages (session_id, role, content, tool_call_id,
                   tool_calls, tool_name, timestamp, token_count, finish_reason,
                   reasoning, reasoning_details, codex_reasoning_items,
                   replay_content, search_content, content_sha256,
                   content_artifacted, content_artifact_kind, content_byte_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    role,
                    stored_content,
                    tool_call_id,
                    json.dumps(tool_calls) if tool_calls else None,
                    tool_name,
                    time.time(),
                    token_count,
                    finish_reason,
                    reasoning,
                    reasoning_details_json,
                    codex_items_json,
                    replay_content,
                    search_content,
                    content_sha,
                    content_artifacted,
                    artifact_kind,
                    content_byte_count,
                ),
            )
            msg_id = cursor.lastrowid
            if artifact_id is not None:
                self._conn.execute(
                    """INSERT OR IGNORE INTO message_artifacts
                       (message_id, artifact_id, purpose, created_at)
                       VALUES (?, ?, 'raw_content', ?)""",
                    (msg_id, artifact_id, time.time()),
                )

            # Update counters
            # Count actual tool calls from the tool_calls list (not from tool responses).
            # A single assistant message can contain multiple parallel tool calls.
            num_tool_calls = 0
            if tool_calls is not None:
                num_tool_calls = len(tool_calls) if isinstance(tool_calls, list) else 1
            if num_tool_calls > 0:
                self._conn.execute(
                    """UPDATE sessions SET message_count = message_count + 1,
                       tool_call_count = tool_call_count + ? WHERE id = ?""",
                    (num_tool_calls, session_id),
                )
            else:
                self._conn.execute(
                    "UPDATE sessions SET message_count = message_count + 1 WHERE id = ?",
                    (session_id,),
                )

            self._conn.commit()
        return msg_id

    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Load all messages for a session, ordered by timestamp."""
        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp, id",
                (session_id,),
            )
            rows = cursor.fetchall()
        result = []
        for row in rows:
            msg = dict(row)
            if msg.get("tool_calls"):
                try:
                    msg["tool_calls"] = json.loads(msg["tool_calls"])
                except (json.JSONDecodeError, TypeError):
                    pass
            result.append(msg)
        return result

    def get_messages_as_conversation(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Load messages in the OpenAI conversation format (role + content dicts).
        Used by the gateway to restore conversation history.
        """
        with self._lock:
            cursor = self._conn.execute(
                "SELECT id, role, content, tool_call_id, tool_calls, tool_name, "
                "reasoning, reasoning_details, codex_reasoning_items, "
                "replay_content, content_sha256, content_artifacted, "
                "content_artifact_kind, content_byte_count, search_content "
                "FROM messages WHERE session_id = ? ORDER BY timestamp, id",
                (session_id,),
            )
            rows = cursor.fetchall()
            exact_replay_ids = set()
            for row in rows[-self.EXACT_RECENT_REPLAY_MESSAGES:]:
                exact_replay_ids.add(row["id"])
            last_tool_call_index = None
            for idx in range(len(rows) - 1, -1, -1):
                row = rows[idx]
                if row["role"] == "assistant" and row["tool_calls"]:
                    last_tool_call_index = idx
                    break
            if last_tool_call_index is not None:
                exact_replay_ids.add(rows[last_tool_call_index]["id"])
                for row in rows[last_tool_call_index + 1:]:
                    if row["role"] == "tool":
                        exact_replay_ids.add(row["id"])
                    elif row["role"] in ("user", "assistant"):
                        break
        messages = []
        seen_artifact_hashes: set[str] = set()
        seen_message_signatures: dict[str, str] = {}
        for row in rows:
            content = row["content"]
            artifact_sha = row["content_sha256"]
            artifact_kind = row["content_artifact_kind"] or self._artifact_kind(row["role"], row["tool_name"])
            artifact_chars = row["content_byte_count"]
            raw_for_signature = None
            legacy_large = (
                not row["content_artifacted"]
                and row["content"] is not None
                and self._should_artifactize(row["role"], row["content"], row["tool_name"])
            )
            if legacy_large:
                with self._lock:
                    exact_content, replay_content, artifact_sha, artifact_kind = self._artifactize_existing_message_locked(row)
                artifact_chars = len(exact_content.encode("utf-8"))
                raw_for_signature = exact_content
                # Large legacy user/assistant prompts are replayed as pointers
                # even when recent; the live current turn is appended separately.
                if row["role"] == "tool" and row["id"] in exact_replay_ids:
                    content = exact_content
                elif artifact_sha in seen_artifact_hashes:
                    content = self._build_duplicate_replay_content(
                        sha256=artifact_sha,
                        kind=artifact_kind,
                        chars=artifact_chars,
                    )
                else:
                    content = replay_content
            elif (
                row["content_artifacted"]
                and row["id"] in exact_replay_ids
                and row["role"] == "tool"
            ):
                with self._lock:
                    exact_content = self._load_artifact_content_locked(row["id"])
                if exact_content is not None:
                    content = exact_content
            elif row["content_artifacted"] and row["replay_content"]:
                if artifact_sha and artifact_sha in seen_artifact_hashes:
                    content = self._build_duplicate_replay_content(
                        sha256=artifact_sha,
                        kind=artifact_kind,
                        chars=artifact_chars,
                    )
                else:
                    content = row["replay_content"]
                    raw_for_signature = row["search_content"] or row["replay_content"] or row["content"]
            if (
                artifact_kind == "message_content"
                and artifact_sha
                and artifact_sha not in seen_artifact_hashes
                and raw_for_signature
            ):
                signature_sha = self._message_evidence_signature(raw_for_signature)
                if signature_sha:
                    prior_sha = seen_message_signatures.get(signature_sha)
                    if prior_sha and prior_sha != artifact_sha:
                        content = self._build_related_replay_content(
                            sha256=artifact_sha,
                            kind=artifact_kind,
                            chars=artifact_chars,
                            signature_sha256=signature_sha,
                            prior_sha256=prior_sha,
                        )
                    else:
                        seen_message_signatures[signature_sha] = artifact_sha
                        refreshed = self._build_replay_content(
                            raw=raw_for_signature,
                            sha256=artifact_sha,
                            kind=artifact_kind,
                        )
                        if row["content_artifacted"] and len(refreshed) < len(content or ""):
                            content = refreshed
                            with self._lock:
                                self._conn.execute(
                                    "UPDATE messages SET content = ?, replay_content = ? WHERE id = ?",
                                    (refreshed, refreshed, row["id"]),
                                )
                                self._conn.commit()
            if artifact_sha:
                seen_artifact_hashes.add(artifact_sha)

            msg = {"role": row["role"], "content": content}
            if row["tool_call_id"]:
                msg["tool_call_id"] = row["tool_call_id"]
            if row["tool_name"]:
                msg["tool_name"] = row["tool_name"]
            if row["tool_calls"]:
                try:
                    msg["tool_calls"] = json.loads(row["tool_calls"])
                except (json.JSONDecodeError, TypeError):
                    pass
            # Restore reasoning fields on assistant messages so providers
            # that replay reasoning (OpenRouter, OpenAI, Nous) receive
            # coherent multi-turn reasoning context.
            if row["role"] == "assistant":
                if row["reasoning"]:
                    msg["reasoning"] = row["reasoning"]
                if row["reasoning_details"]:
                    try:
                        msg["reasoning_details"] = json.loads(row["reasoning_details"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                if row["codex_reasoning_items"]:
                    try:
                        msg["codex_reasoning_items"] = json.loads(row["codex_reasoning_items"])
                    except (json.JSONDecodeError, TypeError):
                        pass
            messages.append(msg)
        return messages

    # =========================================================================
    # Search
    # =========================================================================

    @staticmethod
    def _sanitize_fts5_query(query: str) -> str:
        """Sanitize user input for safe use in FTS5 MATCH queries.

        FTS5 has its own query syntax where characters like ``"``, ``(``, ``)``,
        ``+``, ``*``, ``{``, ``}`` and bare boolean operators (``AND``, ``OR``,
        ``NOT``) have special meaning.  Passing raw user input directly to
        MATCH can cause ``sqlite3.OperationalError``.

        Strategy:
        - Preserve properly paired quoted phrases (``"exact phrase"``)
        - Strip unmatched FTS5-special characters that would cause errors
        - Wrap unquoted hyphenated terms in quotes so FTS5 matches them
          as exact phrases instead of splitting on the hyphen
        """
        # Step 1: Extract balanced double-quoted phrases and protect them
        # from further processing via numbered placeholders.
        _quoted_parts: list = []

        def _preserve_quoted(m: re.Match) -> str:
            _quoted_parts.append(m.group(0))
            return f"\x00Q{len(_quoted_parts) - 1}\x00"

        sanitized = re.sub(r'"[^"]*"', _preserve_quoted, query)

        # Step 2: Strip remaining (unmatched) FTS5-special characters
        sanitized = re.sub(r'[+{}()\"^]', " ", sanitized)

        # Step 3: Collapse repeated * (e.g. "***") into a single one,
        # and remove leading * (prefix-only needs at least one char before *)
        sanitized = re.sub(r"\*+", "*", sanitized)
        sanitized = re.sub(r"(^|\s)\*", r"\1", sanitized)

        # Step 4: Remove dangling boolean operators at start/end that would
        # cause syntax errors (e.g. "hello AND" or "OR world")
        sanitized = re.sub(r"(?i)^(AND|OR|NOT)\b\s*", "", sanitized.strip())
        sanitized = re.sub(r"(?i)\s+(AND|OR|NOT)\s*$", "", sanitized.strip())

        # Step 5: Wrap unquoted hyphenated terms (e.g. ``chat-send``) in
        # double quotes.  FTS5's tokenizer splits on hyphens, turning
        # ``chat-send`` into ``chat AND send``.  Quoting preserves the
        # intended phrase match.
        sanitized = re.sub(r"\b(\w+(?:-\w+)+)\b", r'"\1"', sanitized)

        # Step 6: Restore preserved quoted phrases
        for i, quoted in enumerate(_quoted_parts):
            sanitized = sanitized.replace(f"\x00Q{i}\x00", quoted)

        return sanitized.strip()

    def search_messages(
        self,
        query: str,
        source_filter: List[str] = None,
        exclude_sources: List[str] = None,
        role_filter: List[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Full-text search across session messages using FTS5.

        Supports FTS5 query syntax:
          - Simple keywords: "docker deployment"
          - Phrases: '"exact phrase"'
          - Boolean: "docker OR kubernetes", "python NOT java"
          - Prefix: "deploy*"

        Returns matching messages with session metadata, content snippet,
        and surrounding context (1 message before and after the match).
        """
        if not query or not query.strip():
            return []

        query = self._sanitize_fts5_query(query)
        if not query:
            return []

        # Build WHERE clauses dynamically
        where_clauses = ["messages_fts MATCH ?"]
        params: list = [query]

        if source_filter is not None:
            source_placeholders = ",".join("?" for _ in source_filter)
            where_clauses.append(f"s.source IN ({source_placeholders})")
            params.extend(source_filter)

        if exclude_sources is not None:
            exclude_placeholders = ",".join("?" for _ in exclude_sources)
            where_clauses.append(f"s.source NOT IN ({exclude_placeholders})")
            params.extend(exclude_sources)

        if role_filter:
            role_placeholders = ",".join("?" for _ in role_filter)
            where_clauses.append(f"m.role IN ({role_placeholders})")
            params.extend(role_filter)

        where_sql = " AND ".join(where_clauses)
        params.extend([limit, offset])

        sql = f"""
            SELECT
                m.id,
                m.session_id,
                m.role,
                snippet(messages_fts, 0, '>>>', '<<<', '...', 40) AS snippet,
                COALESCE(m.search_content, m.content) AS content,
                m.timestamp,
                m.tool_name,
                s.source,
                s.model,
                s.started_at AS session_started
            FROM messages_fts
            JOIN messages m ON m.id = messages_fts.rowid
            JOIN sessions s ON s.id = m.session_id
            WHERE {where_sql}
            ORDER BY rank
            LIMIT ? OFFSET ?
        """

        with self._lock:
            try:
                cursor = self._conn.execute(sql, params)
            except sqlite3.OperationalError:
                # FTS5 query syntax error despite sanitization — return empty
                return []
            matches = [dict(row) for row in cursor.fetchall()]

        # Add surrounding context (1 message before + after each match).
        # Done outside the lock so we don't hold it across N sequential queries.
        for match in matches:
            try:
                with self._lock:
                    ctx_cursor = self._conn.execute(
                        """SELECT role, COALESCE(search_content, content) AS content FROM messages
                           WHERE session_id = ? AND id >= ? - 1 AND id <= ? + 1
                           ORDER BY id""",
                        (match["session_id"], match["id"], match["id"]),
                    )
                    context_msgs = [
                        {"role": r["role"], "content": (r["content"] or "")[:200]}
                        for r in ctx_cursor.fetchall()
                    ]
                match["context"] = context_msgs
            except Exception:
                match["context"] = []

        # Remove full content from result (snippet is enough, saves tokens)
        for match in matches:
            match.pop("content", None)

        return matches

    def search_sessions(
        self,
        source: str = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List sessions, optionally filtered by source."""
        with self._lock:
            if source:
                cursor = self._conn.execute(
                    "SELECT * FROM sessions WHERE source = ? ORDER BY started_at DESC LIMIT ? OFFSET ?",
                    (source, limit, offset),
                )
            else:
                cursor = self._conn.execute(
                    "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                )
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Utility
    # =========================================================================

    def session_count(self, source: str = None) -> int:
        """Count sessions, optionally filtered by source."""
        with self._lock:
            if source:
                cursor = self._conn.execute(
                    "SELECT COUNT(*) FROM sessions WHERE source = ?", (source,)
                )
            else:
                cursor = self._conn.execute("SELECT COUNT(*) FROM sessions")
            return cursor.fetchone()[0]

    def message_count(self, session_id: str = None) -> int:
        """Count messages, optionally for a specific session."""
        with self._lock:
            if session_id:
                cursor = self._conn.execute(
                    "SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,)
                )
            else:
                cursor = self._conn.execute("SELECT COUNT(*) FROM messages")
            return cursor.fetchone()[0]

    # =========================================================================
    # Export and cleanup
    # =========================================================================

    def export_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Export a single session with all its messages as a dict."""
        session = self.get_session(session_id)
        if not session:
            return None
        messages = self.get_messages(session_id)
        return {**session, "messages": messages}

    def export_all(self, source: str = None) -> List[Dict[str, Any]]:
        """
        Export all sessions (with messages) as a list of dicts.
        Suitable for writing to a JSONL file for backup/analysis.
        """
        sessions = self.search_sessions(source=source, limit=100000)
        results = []
        for session in sessions:
            messages = self.get_messages(session["id"])
            results.append({**session, "messages": messages})
        return results

    def clear_messages(self, session_id: str) -> None:
        """Delete all messages for a session and reset its counters."""
        with self._lock:
            self._conn.execute(
                "DELETE FROM messages WHERE session_id = ?", (session_id,)
            )
            self._conn.execute(
                "UPDATE sessions SET message_count = 0, tool_call_count = 0 WHERE id = ?",
                (session_id,),
            )
            self._conn.commit()

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages. Returns True if found."""
        with self._lock:
            cursor = self._conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE id = ?", (session_id,)
            )
            if cursor.fetchone()[0] == 0:
                return False
            self._conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            self._conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            self._conn.commit()
            return True

    def prune_sessions(self, older_than_days: int = 90, source: str = None) -> int:
        """
        Delete sessions older than N days. Returns count of deleted sessions.
        Only prunes ended sessions (not active ones).
        """
        import time as _time
        cutoff = _time.time() - (older_than_days * 86400)

        with self._lock:
            if source:
                cursor = self._conn.execute(
                    """SELECT id FROM sessions
                       WHERE started_at < ? AND ended_at IS NOT NULL AND source = ?""",
                    (cutoff, source),
                )
            else:
                cursor = self._conn.execute(
                    "SELECT id FROM sessions WHERE started_at < ? AND ended_at IS NOT NULL",
                    (cutoff,),
                )
            session_ids = [row["id"] for row in cursor.fetchall()]

            for sid in session_ids:
                self._conn.execute("DELETE FROM messages WHERE session_id = ?", (sid,))
                self._conn.execute("DELETE FROM sessions WHERE id = ?", (sid,))

            self._conn.commit()
        return len(session_ids)
