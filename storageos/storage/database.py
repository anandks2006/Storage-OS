"""SQLite database schema, init, and connection management."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from core.models import (
    Passage,
    RepresentationManifest,
    ResourceIdentity,
    ResourceVersion,
    SourceType,
    StructuralNode,
    VersionStatus,
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS spaces (
    space_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    root_path TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS resources (
    resource_id TEXT PRIMARY KEY,
    space_id TEXT NOT NULL,
    absolute_path TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    extension TEXT NOT NULL,
    size INTEGER NOT NULL,
    mtime REAL NOT NULL,
    content_hash TEXT,
    source_type TEXT NOT NULL,
    first_seen REAL NOT NULL,
    last_seen REAL NOT NULL,
    FOREIGN KEY (space_id) REFERENCES spaces(space_id)
);

CREATE TABLE IF NOT EXISTS resource_versions (
    version_id TEXT PRIMARY KEY,
    resource_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    timestamp REAL NOT NULL,
    size INTEGER NOT NULL,
    mtime REAL NOT NULL,
    FOREIGN KEY (resource_id) REFERENCES resources(resource_id)
);

CREATE TABLE IF NOT EXISTS structural_nodes (
    node_id TEXT PRIMARY KEY,
    resource_id TEXT NOT NULL,
    version_id TEXT NOT NULL,
    node_type TEXT NOT NULL,
    level INTEGER NOT NULL DEFAULT 0,
    title TEXT NOT NULL DEFAULT '',
    start_offset INTEGER NOT NULL DEFAULT 0,
    end_offset INTEGER NOT NULL DEFAULT 0,
    parent_id TEXT,
    FOREIGN KEY (resource_id) REFERENCES resources(resource_id),
    FOREIGN KEY (version_id) REFERENCES resource_versions(version_id)
);

CREATE TABLE IF NOT EXISTS passages (
    passage_id TEXT PRIMARY KEY,
    resource_id TEXT NOT NULL,
    version_id TEXT NOT NULL,
    node_id TEXT,
    text TEXT NOT NULL,
    start_offset INTEGER NOT NULL DEFAULT 0,
    end_offset INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (resource_id) REFERENCES resources(resource_id),
    FOREIGN KEY (version_id) REFERENCES resource_versions(version_id),
    FOREIGN KEY (node_id) REFERENCES structural_nodes(node_id)
);

CREATE TABLE IF NOT EXISTS representation_manifests (
    manifest_id TEXT PRIMARY KEY,
    resource_id TEXT NOT NULL,
    version_id TEXT NOT NULL,
    identity_rep INTEGER NOT NULL DEFAULT 1,
    structure_rep INTEGER NOT NULL DEFAULT 1,
    lexical_rep INTEGER NOT NULL DEFAULT 1,
    semantic_rep INTEGER NOT NULL DEFAULT 0,
    vector_rep INTEGER NOT NULL DEFAULT 0,
    graph_rep INTEGER NOT NULL DEFAULT 0,
    representation_version TEXT NOT NULL DEFAULT '0.1',
    FOREIGN KEY (resource_id) REFERENCES resources(resource_id),
    FOREIGN KEY (version_id) REFERENCES resource_versions(version_id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS passages_fts USING fts5(
    passage_id,
    resource_id,
    text,
    content='passages',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS passages_ai AFTER INSERT ON passages BEGIN
    INSERT INTO passages_fts(passage_id, resource_id, text) VALUES (new.passage_id, new.resource_id, new.text);
END;

CREATE TRIGGER IF NOT EXISTS passages_ad AFTER DELETE ON passages BEGIN
    INSERT INTO passages_fts(passages_fts, passage_id, resource_id, text) VALUES('delete', old.passage_id, old.resource_id, old.text);
END;

CREATE TRIGGER IF NOT EXISTS passages_au AFTER UPDATE ON passages BEGIN
    INSERT INTO passages_fts(passages_fts, passage_id, resource_id, text) VALUES('delete', old.passage_id, old.resource_id, old.text);
    INSERT INTO passages_fts(passage_id, resource_id, text) VALUES (new.passage_id, new.resource_id, new.text);
END;

CREATE INDEX IF NOT EXISTS idx_versions_resource ON resource_versions(resource_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_passages_resource ON passages(resource_id);
CREATE INDEX IF NOT EXISTS idx_nodes_resource ON structural_nodes(resource_id);
CREATE INDEX IF NOT EXISTS idx_manifests_resource ON representation_manifests(resource_id);
"""


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        if self.conn is None:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA foreign_keys=ON")
        return self.conn

    def init_schema(self) -> None:
        conn = self.connect()
        conn.executescript(SCHEMA_SQL)
        conn.commit()

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def create_space(self, name: str, root_path: str, created_at: float) -> str:
        import uuid
        space_id = f"space-{uuid.uuid4().hex[:12]}"
        self.connect().execute(
            "INSERT INTO spaces (space_id, name, root_path, created_at) VALUES (?, ?, ?, ?)",
            (space_id, name, root_path, created_at),
        )
        self.conn.commit()
        return space_id

    def upsert_resource(self, res: ResourceIdentity, space_id: str) -> None:
        conn = self.connect()
        conn.execute(
            """INSERT INTO resources (resource_id, space_id, absolute_path, filename, extension, size, mtime, content_hash, source_type, first_seen, last_seen)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(absolute_path) DO UPDATE SET
                   filename=excluded.filename,
                   extension=excluded.extension, size=excluded.size, mtime=excluded.mtime,
                   content_hash=excluded.content_hash, source_type=excluded.source_type,
                   last_seen=excluded.last_seen""",
            (res.resource_id, space_id, res.absolute_path, res.filename, res.extension,
             res.size, res.mtime, res.content_hash, res.source_type.value,
             res.first_seen, res.last_seen),
        )
        conn.commit()

    def get_resource_by_path(self, absolute_path: str) -> Optional[dict]:
        row = self.connect().execute(
            "SELECT * FROM resources WHERE absolute_path = ?", (absolute_path,)
        ).fetchone()
        return dict(row) if row else None

    def get_resource_by_id(self, resource_id: str) -> Optional[dict]:
        row = self.connect().execute(
            "SELECT * FROM resources WHERE resource_id = ?", (resource_id,)
        ).fetchone()
        return dict(row) if row else None

    def insert_version(self, ver: ResourceVersion) -> None:
        conn = self.connect()
        conn.execute(
            """INSERT OR REPLACE INTO resource_versions (version_id, resource_id, content_hash, status, timestamp, size, mtime)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (ver.version_id, ver.resource_id, ver.content_hash, ver.status.value,
             ver.timestamp, ver.size, ver.mtime),
        )
        conn.commit()

    def get_latest_version(self, resource_id: str) -> Optional[dict]:
        row = self.connect().execute(
            "SELECT * FROM resource_versions WHERE resource_id = ? ORDER BY timestamp DESC LIMIT 1",
            (resource_id,),
        ).fetchone()
        return dict(row) if row else None

    def insert_structural_node(self, node: StructuralNode) -> None:
        conn = self.connect()
        conn.execute(
            """INSERT OR REPLACE INTO structural_nodes (node_id, resource_id, version_id, node_type, level, title, start_offset, end_offset, parent_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (node.node_id, node.resource_id, node.version_id, node.node_type,
             node.level, node.title, node.start_offset, node.end_offset, node.parent_id),
        )
        conn.commit()

    def insert_passage(self, passage: Passage) -> None:
        conn = self.connect()
        conn.execute(
            """INSERT OR REPLACE INTO passages (passage_id, resource_id, version_id, node_id, text, start_offset, end_offset)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (passage.passage_id, passage.resource_id, passage.version_id,
             passage.node_id, passage.text, passage.start_offset, passage.end_offset),
        )
        conn.commit()

    def insert_manifest(self, manifest: RepresentationManifest) -> None:
        conn = self.connect()
        conn.execute(
            """INSERT OR REPLACE INTO representation_manifests
               (manifest_id, resource_id, version_id, identity_rep, structure_rep, lexical_rep, semantic_rep, vector_rep, graph_rep, representation_version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (manifest.manifest_id, manifest.resource_id, manifest.version_id,
             int(manifest.identity), int(manifest.structure), int(manifest.lexical),
             int(manifest.semantic), int(manifest.vector), int(manifest.graph),
             manifest.representation_version),
        )
        conn.commit()

    @staticmethod
    def _sanitize_fts_query(query: str) -> str:
        """Escape special FTS5 characters and build a simple OR query."""
        import re
        tokens = re.findall(r"\w+", query)
        if not tokens:
            return '""'
        # Use double-quoted phrases for each token to avoid FTS5 operator issues
        safe_tokens = [f'"{t}"' for t in tokens]
        return " OR ".join(safe_tokens)

    def search_fts(self, query: str, limit: int = 20) -> list[dict]:
        safe_query = self._sanitize_fts_query(query)
        rows = self.connect().execute(
            """SELECT f.passage_id, f.resource_id, f.text, p.start_offset, p.end_offset, p.node_id
               FROM passages_fts f
               JOIN passages p ON p.passage_id = f.passage_id
               WHERE passages_fts MATCH ?
               ORDER BY rank
               LIMIT ?""",
            (safe_query, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_resources(self) -> list[dict]:
        rows = self.connect().execute("SELECT * FROM resources").fetchall()
        return [dict(r) for r in rows]

    def get_passages_for_resource(self, resource_id: str) -> list[dict]:
        rows = self.connect().execute(
            "SELECT * FROM passages WHERE resource_id = ?", (resource_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_nodes_for_resource(self, resource_id: str) -> list[dict]:
        rows = self.connect().execute(
            "SELECT * FROM structural_nodes WHERE resource_id = ?", (resource_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_passage_by_id(self, passage_id: str) -> Optional[dict]:
        row = self.connect().execute(
            "SELECT * FROM passages WHERE passage_id = ?", (passage_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_all_nodes(self) -> list[dict]:
        """Return all structural nodes grouped by resource_id."""
        rows = self.connect().execute("SELECT * FROM structural_nodes").fetchall()
        return [dict(r) for r in rows]

    def get_all_passages(self) -> list[dict]:
        """Return all passages grouped by resource_id."""
        rows = self.connect().execute("SELECT * FROM passages").fetchall()
        return [dict(r) for r in rows]
